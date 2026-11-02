import datetime
import re
import jdatetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from hijri_converter import Gregorian, Hijri
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# تنظیمات صفحه
# ---------------------------------------------------------
st.set_page_config(
    page_title="سامانه جامع هوشمند ایران", page_icon="", layout="wide"
)

# ---------------------------------------------------------
# سایدبار و تم
# ---------------------------------------------------------
st.sidebar.title("تنظيمات")
theme_mode = st.sidebar.selectbox("حالت صفحه", ["شب (Dark)", "روز (Light)"])
font_size = st.sidebar.slider("اندازه فونت", 12, 28, 16)

if theme_mode == "شب (Dark)":
  bg_color, text_color = "#0f172a", "#f8fafc"
else:
  bg_color, text_color = "#f8fafc", "#0f172a"

st.markdown(
    f"""
<style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
        font-size: {font_size}px;
    }}
    h1, h2, h3, h4, h5, h6, p, span, label {{
        color: {text_color} !important;
    }}
    .stButton > button {{
        background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%);
        color: #fff;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: bold;
        border: none;
    }}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# دیکشنری‌های کمکی
# ---------------------------------------------------------
PERSIAN_MONTHS = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهريور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
]
HIJRI_MONTHS = [
    "محرم",
    "صفر",
    "ربيع الأول",
    "ربيع الثاني",
    "جمادى الأول",
    "جمادى الثاني",
    "رجب",
    "شعبان",
    "رمضان",
    "شوال",
    "ذى القعده",
    "ذي الحجه",
]
GREGORIAN_MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
DAYS_FA = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنجشنبه",
    "Friday": "جمعه",
}


def show_toast():
  toast = st.session_state.pop("toast", None)
  if toast:
    kind, message = toast
    st.toast(message, icon="✅" if kind == "success" else "⚠️")


def set_toast(kind, message):
  st.session_state["toast"] = (kind, message)


def next_id(key):
  session_key = f"_id_{key}"
  if session_key not in st.session_state:
    st.session_state[session_key] = 1
  val = st.session_state[session_key]
  st.session_state[session_key] += 1
  return val


# ---------------------------------------------------------
# بازار زنده - با cache هیبرید
# ---------------------------------------------------------
@st.cache_data(ttl=5, show_spinner=False)
def _fetch_usd_price():
  response = requests.get(
      "https://api.nobitex.ir/v2/orderbook/USDTIRT",
      timeout=5,
      headers={"User-Agent": "IranSmartSystem/1.0"},
  )
  response.raise_for_status()
  bids = response.json().get("bids")
  if not bids or not bids[0]:
    raise ValueError("قیمت معتبری دریافت نشد.")
  return float(bids[0][0]) / 10


def fetch_live_market_prices():
  try:
    usd = _fetch_usd_price()
    result = {
        "USD": usd,
        "EUR": usd * 1.13,
        "GBP": usd * 1.34,
        "AED": usd * 0.27,
        "status": "آخرین نرخ دریافت شده از بازار",
        "updated_at": datetime.datetime.now().strftime("%H:%M:%S"),
        "live": True,
    }
    st.session_state["last_market_price"] = result
    return result
  except (
      requests.RequestException,
      ValueError,
      KeyError,
      IndexError,
      TypeError,
  ) as error:
    if "last_market_price" in st.session_state:
      result = st.session_state["last_market_price"].copy()
      result["status"] = (
          f"اتصال جدید برقرار نشد. (آخرین قیمت معتبر: {type(error).__name__})"
      )
      result["live"] = False
      return result
    return {
        "USD": 0,
        "EUR": 0,
        "GBP": 0,
        "AED": 0,
        "status": f"دریافت قیمت ناموفق بود ({type(error).__name__})",
        "updated_at": "-",
        "live": False,
    }


# ---------------------------------------------------------
# منو
# ---------------------------------------------------------
MENU = {
    "market": "بازار زنده و مبدل ارز",
    "finance": "مدیریت مالی کسر روزانه از حقوق",
    "debts": "مدیریت بدهی ها و قرضها",
    "tasks": "مديريت وظايف",
    "reminders": "يادآور رویدادها",
    "weather": "آب وهوا",
    "clock": "ساعت زنده و مبدل تقویم",
}

selected = st.sidebar.radio(
    "منوی اصلی", list(MENU.keys()), format_func=lambda key: MENU[key]
)

if st.sidebar.button("بروزرسانی نرخ‌ها"):
  _fetch_usd_price.clear()
  st.session_state.pop("last_market_price", None)
  set_toast("success", "نرخ‌ها بروزرسانی شد.")
  st.rerun()

show_toast()

# =========================================================
# ۱ - بازار
# =========================================================
if selected == "market":
  st_autorefresh(interval=5000, key="market_refresh")
  st.header("بازار زنده و مبدل ارز")
  market = fetch_live_market_prices()
  st.caption(market["status"])
  st.caption(f"آخرین دریافت قیمت: {market['updated_at']}")

  if market["USD"] == 0:
    st.error(
        "قیمت زنده در حال حاضر در دسترس نیست. اتصال اینترنت و API را بررسی"
        " کنید."
    )
  else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("USDT", f"{market['USD']:,.0f} تومان")
    c2.metric("یورو تقریبی", f"{market['EUR']:,.0f} تومان")
    c3.metric("پوند تقریبی", f"{market['GBP']:,.0f} تومان")
    c4.metric("درهم تقریبی", f"{market['AED']:,.0f} تومان")

    st.markdown("---")
    st.subheader("مبدل ارز به تومان")
    currencies = {
        "دلار / USDT": market["USD"],
        "یورو (تقریبی)": market["EUR"],
        "پوند (تقریبی)": market["GBP"],
        "درهم (تقریبی)": market["AED"],
    }
    mc1, mc2 = st.columns(2)
    chosen = mc1.selectbox("انتخاب ارز:", list(currencies.keys()))
    amount = mc2.number_input("مقدار:", min_value=0.0, value=1.0, step=1.0)
    res = amount * currencies[chosen]
    st.success(f"معادل: {res:,.0f} تومان")

# =========================================================
# ۲ - مدیریت مالی
# =========================================================
elif selected == "finance":
  st.header("مدیریت مالی - کسر خودکار هزینه ها از حقوق")

  if "salary" not in st.session_state:
    st.session_state["salary"] = 25_000_000
  if "transactions" not in st.session_state:
    st.session_state["transactions"] = []

  sc1, sc2 = st.columns([3, 1])
  new_salary = sc1.number_input(
      "حقوق ماه (تومان)",
      min_value=0,
      value=st.session_state["salary"],
      step=500_000,
  )
  if sc2.button("ثبت حقوق"):
    st.session_state["salary"] = new_salary
    set_toast("success", "حقوق ثبت شد.")
    st.rerun()

  total_spent = sum(
      transaction["مبلغ"] for transaction in st.session_state["transactions"]
  )
  remaining = st.session_state["salary"] - total_spent

  mm1, mm2, mm3 = st.columns(3)
  mm1.metric("حقوق کل", f"{st.session_state['salary']:,.0f} تومان")
  mm2.metric("مجموع هزینه", f"{total_spent:,.0f} تومان")
  mm3.metric("مانده", f"{remaining:,.0f} تومان", delta=f"{-total_spent:,.0f}")

  st.markdown("---")
  st.subheader("ثبت هزینه روزانه")

  current_jalali_year = jdatetime.date.today().year
  available_years = [
      str(current_jalali_year),
      str(current_jalali_year + 1),
      str(current_jalali_year + 2),
  ]

  with st.form("add_tx"):
    f1, f2, f3, f4 = st.columns(4)
    selected_year = f1.selectbox("سال", available_years)
    selected_month = f2.selectbox("ماه", PERSIAN_MONTHS)
    category = f3.selectbox(
        "دسته",
        [
            "قبض آب",
            "قبض برق و گاز",
            "خرید خوراکی",
            "تفريح",
            "سفر",
            "پس انداز",
            "ساير",
        ],
    )
    amount = f4.number_input("مبلغ (تومان)", min_value=0, step=50000)

    if st.form_submit_button("ثبت و کسر از حقوق"):
      if amount <= 0:
        st.error("مبلغ باید بزرگتر از صفر باشد.")
      else:
        st.session_state["transactions"].append({
            "id": next_id("tx"),
            "سال": selected_year,
            "ماه": selected_month,
            "دسته": category,
            "مبلغ": amount,
        })
        set_toast("success", "هزینه ثبت شد.")
        st.rerun()

  if st.session_state["transactions"]:
    st.markdown("---")
    st.subheader("لیست هزینه ها")
    for transaction in list(st.session_state["transactions"]):
      cc1, cc2 = st.columns([5, 1])
      cc1.info(
          f"ماه: {transaction['ماه']} {transaction['سال']} | دسته:"
          f" {transaction['دسته']} | مبلغ: {transaction['مبلغ']:,.0f} تومان"
      )
      if cc2.button("حذف", key=f"del_tx_{transaction['id']}"):
        st.session_state["transactions"] = [
            item
            for item in st.session_state["transactions"]
            if item["id"] != transaction["id"]
        ]
        set_toast("success", "حذف شد.")
        st.rerun()

    dataframe = pd.DataFrame(st.session_state["transactions"])
    dataframe["دوره"] = dataframe["سال"] + " " + dataframe["ماه"]
    ordered_periods = []
    for year in available_years:
      for month in PERSIAN_MONTHS:
        period = f"{month} {year}"
        if period in dataframe["دوره"].values:
          ordered_periods.append(period)

    if not dataframe.empty:
      figure = px.bar(
          dataframe,
          x="دوره",
          y="مبلغ",
          color="دسته",
          title="مقایسه هزینه ها",
          category_orders={"دوره": ordered_periods},
      )
      figure.update_xaxes(tickangle=-45)
      st.plotly_chart(figure, use_container_width=True)

# =========================================================
# ۳ - بدهی ها
# =========================================================
elif selected == "debts":
  st.header("مدیریت بدهی ها و قرضها")
  if "debts" not in st.session_state:
    st.session_state["debts"] = []

  with st.form("add_debt"):
    d1, d2, d3, d4 = st.columns(4)
    name = d1.text_input("نام شخص")
    kind = d2.selectbox(
        "نوع:", ["قرض گرفتم (بدهکارم)", "قرض دادم (طلبکارم)"]
    )
    amount = d3.number_input("مبلغ (تومان)", min_value=0, step=100000)
    due = d4.text_input("موعد (مثلاً ۱۵ اسفند)")

    if st.form_submit_button("ثبت"):
      if not name.strip():
        st.error("نام شخص را وارد کنید.")
      elif amount <= 0:
        st.error("مبلغ باید بزرگتر از صفر باشد.")
      else:
        st.session_state["debts"].append({
            "id": next_id("debt"),
            "شخص": name.strip(),
            "نوع": kind,
            "مبلغ": amount,
            "موعد": due,
            "وضعیت": "در انتظار تسویه",
        })
        set_toast("success", "بدهی ثبت شد.")
        st.rerun()

  if st.session_state["debts"]:
    st.markdown("---")
    for debt in list(st.session_state["debts"]):
      bc1, bc2, bc3 = st.columns([4, 1, 1])
      bc1.info(
          f"شخص: {debt['شخص']} | نوع: {debt['نوع']} | مبلغ:"
          f" {debt['مبلغ']:,.0f} تومان | موعد: {debt['موعد']} | وضعیت:"
          f" {debt['وضعیت']}"
      )
      if bc2.button("تسویه", key=f"pay_debt_{debt['id']}"):
        for item in st.session_state["debts"]:
          if item["id"] == debt["id"]:
            item["وضعیت"] = "تسویه شد"
        set_toast("success", "تسویه ثبت شد.")
        st.rerun()
      if bc3.button("حذف", key=f"del_debt_{debt['id']}"):
        st.session_state["debts"] = [
            item
            for item in st.session_state["debts"]
            if item["id"] != debt["id"]
        ]
        set_toast("success", "حذف شد.")
        st.rerun()

# =========================================================
# ۴ - وظايف
# =========================================================
elif selected == "tasks":
  st.header("مديريت وظايف")
  if "tasks" not in st.session_state:
    st.session_state["tasks"] = []

  tc1, tc2 = st.columns(2)
  title = tc1.text_input("عنوان وظيفه")
  priority = tc2.selectbox("اولویت", ["بالا", "متوسط", "پایین"])

  if st.button("افزودن"):
    if not title.strip():
      st.error("عنوان را وارد کنید.")
    else:
      st.session_state["tasks"].append({
          "id": next_id("task"),
          "عنوان": title.strip(),
          "اولویت": priority,
          "وضعیت": "در انتظار",
      })
      set_toast("success", "وظیفه اضافه شد.")
      st.rerun()

  if st.session_state["tasks"]:
    st.markdown("---")
    filter_value = st.selectbox(
        "فيلتر:", ["همه", "در انتظار", "انجام شده", "انجام نشده"]
    )
    for task in list(st.session_state["tasks"]):
      if filter_value == "در انتظار" and "در انتظار" not in task["وضعیت"]:
        continue
      if filter_value == "انجام شده" and "انجام شد" not in task["وضعیت"]:
        continue
      if filter_value == "انجام نشده" and "انجام نشد" not in task["وضعیت"]:
        continue

      c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
      c1.info(
          f"عنوان: {task['عنوان']} | اولویت: {task['اولویت']} | وضعیت:"
          f" {task['وضعیت']}"
      )
      if c2.button("✅", key=f"done_{task['id']}"):
        for item in st.session_state["tasks"]:
          if item["id"] == task["id"]:
            item["وضعیت"] = "انجام شد"
        st.rerun()
      if c3.button("❌", key=f"fail_{task['id']}"):
        for item in st.session_state["tasks"]:
          if item["id"] == task["id"]:
            item["وضعیت"] = "انجام نشد"
        st.rerun()
      if c4.button("🗑️", key=f"del_task_{task['id']}"):
        st.session_state["tasks"] = [
            item
            for item in st.session_state["tasks"]
            if item["id"] != task["id"]
        ]
        set_toast("success", "حذف شد.")
        st.rerun()

# =========================================================
# ۵ - یادآورها
# =========================================================
elif selected == "reminders":
  st.header("يادآور رویدادها")
  if "reminders" not in st.session_state:
    st.session_state["reminders"] = []

  calendar_type = st.radio(
      "تقويم:", ["شمسي", "قمری", "میلادی"], horizontal=True
  )
  if calendar_type == "شمسي":
    month_options = PERSIAN_MONTHS
  elif calendar_type == "قمری":
    month_options = HIJRI_MONTHS
  else:
    month_options = GREGORIAN_MONTHS

  r1, r2, r3 = st.columns(3)
  hour = r1.text_input("ساعت (HH:MM):", value="12:00")
  day = r2.number_input("روز", min_value=1, max_value=31, value=1, step=1)
  month = r3.selectbox("ماه", month_options)

  r4, r5, r6 = st.columns(3)
  reminder_title = r4.text_input("عنوان")
  note = r5.text_input("یادداشت", value="")
  remind_day_before = r6.checkbox("هشدار روز قبل", value=True)

  if st.button("ثبت یادآور"):
    if not reminder_title.strip():
      st.error("عنوان را وارد کنید.")
    elif not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hour.strip()):
      st.error("ساعت باید به فرمت HH:MM و بین ۰۰:۰۰ تا ۲۳:۵۹ باشد.")
    else:
      st.session_state["reminders"].append({
          "id": next_id("rem"),
          "تقويم": calendar_type,
          "ساعت": hour.strip(),
          "روز": int(day),
          "ماه": month,
          "عنوان": reminder_title.strip(),
          "یادداشت": note,
          "هشدار": "فعال" if remind_day_before else "-",
          "وضعیت": "در انتظار",
      })
      set_toast("success", "یادآور ثبت شد.")
      st.rerun()

  if st.session_state["reminders"]:
    st.markdown("---")
    filter_value = st.selectbox(
        "فيلتر:", ["همه", "در انتظار", "انجام شده", "انجام نشده"], key="rem_filt"
    )
    for reminder in list(st.session_state["reminders"]):
      if filter_value == "در انتظار" and "در انتظار" not in reminder["وضعیت"]:
        continue
      if filter_value == "انجام شده" and "انجام شد" not in reminder["وضعیت"]:
        continue
      if filter_value == "انجام نشده" and "انجام نشد" not in reminder["وضعیت"]:
        continue

      c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
      c1.info(
          f"عنوان: {reminder['عنوان']} | تقویم: {reminder['تقويم']} - ماه:"
          f" {reminder['ماه']}، روز: {reminder['روز']} | ساعت: {reminder['ساعت']}"
          f" | هشدار: {reminder['هشدار']} | وضعیت: {reminder['وضعیت']}"
      )
      if c2.button("✅", key=f"rdone_{reminder['id']}"):
        for item in st.session_state["reminders"]:
          if item["id"] == reminder["id"]:
            item["وضعیت"] = "انجام شد"
        st.rerun()
      if c3.button("❌", key=f"rfail_{reminder['id']}"):
        for item in st.session_state["reminders"]:
          if item["id"] == reminder["id"]:
            item["وضعیت"] = "انجام نشد"
        st.rerun()
      if c4.button("🗑️", key=f"rdel_{reminder['id']}"):
        st.session_state["reminders"] = [
            item
            for item in st.session_state["reminders"]
            if item["id"] != reminder["id"]
        ]
        set_toast("success", "حذف شد.")
        st.rerun()

# =========================================================
# ۶ - آب و هوا
# =========================================================
elif selected == "weather":
  st.header("وضعیت آب و هوا")
  CITY_MAP = {
      "بندرعباس": "Bandar Abbas",
      "تهران": "Tehran",
      "مشهد": "Mashhad",
      "اصفهان": "Isfahan",
      "شیراز": "Shiraz",
      "تبريز": "Tabriz",
      "اهواز": "Ahvaz",
      "قم": "Qom",
      "کرج": "Karaj",
      "رشت": "Rasht",
      "کرمان": "Kerman",
      "یزد": "Yazd",
      "کیش": "Kish",
      "قشم": "Qeshm",
      "بوشهر": "Bushehr",
      "اروميه": "Urmia",
      "زاهدان": "Zahedan",
      "همدان": "Hamadan",
      "سنندج": "Sanandaj",
      "گرگان": "Gorgan",
  }
  city = st.text_input("نام شهر", value="بندرعباس")
  if st.button("دریافت وضعیت"):
    query = CITY_MAP.get(city.strip(), city.strip())
    with st.spinner("در حال دریافت..."):
      try:
        response = requests.get(f"https://wttr.in/{query}?format=j1", timeout=8)
        if response.status_code == 200:
          current = response.json()["current_condition"][0]
          st.success(f"شهر: {city}")
          w1, w2, w3, w4 = st.columns(4)
          w1.metric("دما", f"{current['temp_C']} °C")
          w2.metric("وضعیت", current["weatherDesc"][0]["value"])
          w3.metric("رطوبت", f"{current['humidity']}%")
          w4.metric("سرعت باد", f"{current['windspeedKmph']} km/h")
        else:
          st.warning("سرور هواشناسی پاسخ نداد. بعداً تلاش کنید.")
      except requests.RequestException as error:
        st.error(f"خطای شبکه: {type(error).__name__}")

# =========================================================
# ۷ - ساعت و تقویم
# =========================================================
elif selected == "clock":
  st.header("ساعت زنده و مبدل تقویم")
  live = st.checkbox("ساعت زنده بروزرسانی هر ۱ ثانیه", value=True)
  if live:
    st_autorefresh(interval=1000, key="clock_tick")

  now = datetime.datetime.now()
  jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
  hijri_now = Gregorian(now.year, now.month, now.day).to_hijri()
  day_fa = DAYS_FA.get(now.strftime("%A"), "")

  st.success(
      f"ساعت زنده: {now.strftime('%H:%M:%S')}\n\nروز هفته: {day_fa}\nمیلادی:"
      f" {now.strftime('%Y-%m-%d')}\nشمسی:"
      f" {jalali_now.strftime('%Y/%m/%d')} ({PERSIAN_MONTHS[jalali_now.month - 1]}"
      f" {jalali_now.day}, {jalali_now.year})\nقمری: {hijri_now.day}"
      f" {HIJRI_MONTHS[hijri_now.month - 1]} {hijri_now.year}"
  )

  st.markdown("---")
  st.subheader("مبدل تقویم")
  source_calendar = st.selectbox("از:", ["میلادی", "شمسي", "قمری"])
  destination_calendar = st.selectbox(
      "به:", [c for c in ["میلادی", "شمسي", "قمری"] if c != source_calendar]
  )

  if source_calendar == "میلادی":
    c1, c2, c3 = st.columns(3)
    year = c1.number_input("سال میلادی", 1900, 2100, now.year)
    month = c2.number_input("ماه میلادی", 1, 12, now.month)
    day = c3.number_input(
        "روز میلادی", 1, 31, min(now.day, 31)
    )  # روز ایمن‌شده
    if st.button("تبديل"):
      try:
        gregorian_date = datetime.date(int(year), int(month), int(day))
        jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
        hijri_date = Gregorian(
            gregorian_date.year, gregorian_date.month, gregorian_date.day
        ).to_hijri()
        day_name = DAYS_FA.get(gregorian_date.strftime("%A"), "")

        if destination_calendar == "شمسي":
          st.info(
              f"تاریخ شمسی: {jalali_date.year}/{jalali_date.month:02d}/{jalali_date.day:02d}"
              f" ({PERSIAN_MONTHS[jalali_date.month - 1]} {jalali_date.day},"
              f" {jalali_date.year}) - {day_name}"
          )
        elif destination_calendar == "قمری":
          st.info(
              f"تاریخ قمری: {hijri_date.day} {HIJRI_MONTHS[hijri_date.month - 1]}"
              f" {hijri_date.year} - {day_name}"
          )
      except ValueError as error:
        st.error(f"تاریخ نامعتبر: {error}")

  elif source_calendar == "شمسي":
    current_jalali_year = jdatetime.date.today().year
    c1, c2, c3 = st.columns(3)
    year = c1.number_input("سال شمسی", 1300, 1500, current_jalali_year)
    month = c2.number_input("ماه شمسی", 1, 12, 1)
    day = c3.number_input("روز شمسی", 1, 31, 1)
    if st.button("تبديل"):
      try:
        jalali_date = jdatetime.date(int(year), int(month), int(day))
        gregorian_date = jalali_date.togregorian()
        day_name = DAYS_FA.get(gregorian_date.strftime("%A"), "")

        if destination_calendar == "میلادی":
          st.info(
              f"تاریخ میلادی: {gregorian_date.year}-{gregorian_date.month:02d}-{gregorian_date.day:02d}"
              f" - {day_name}"
          )
        elif destination_calendar == "قمری":
          hijri_date = Gregorian(
              gregorian_date.year, gregorian_date.month, gregorian_date.day
          ).to_hijri()
          st.info(
              f"تاریخ قمری: {hijri_date.day} {HIJRI_MONTHS[hijri_date.month - 1]}"
              f" {hijri_date.year} - {day_name}"
          )
      except ValueError as error:
        st.error(f"تاریخ نامعتبر: {error}")

  elif source_calendar == "قمری":
    c1, c2, c3 = st.columns(3)
    year = c1.number_input("سال قمری", 1300, 1500, 1448)
    month = c2.number_input("ماه قمری", 1, 12, 1)
    day = c3.number_input("روز قمری", 1, 30, 1)
    if st.button("تبديل"):
      try:
        hijri_date = Hijri(int(year), int(month), int(day))
        gregorian_date = hijri_date.to_gregorian()
        date_value = datetime.date(
            gregorian_date.year, gregorian_date.month, gregorian_date.day
        )
        day_name = DAYS_FA.get(date_value.strftime("%A"), "")

        if destination_calendar == "میلادی":
          st.info(
              f"تاریخ میلادی: {gregorian_date.year}-{gregorian_date.month:02d}-{gregorian_date.day:02d}"
              f" - {day_name}"
          )
        elif destination_calendar == "شمسي":
          jalali_date = jdatetime.date.fromgregorian(date=date_value)
          st.info(
              f"تاریخ شمسی: {jalali_date.year}/{jalali_date.month:02d}/{jalali_date.day:02d}"
              f" ({PERSIAN_MONTHS[jalali_date.month - 1]} {jalali_date.day},"
              f" {jalali_date.year}) - {day_name}"
          )
      except ValueError as error:
        st.error(f"تاریخ نامعتبر: {error}")