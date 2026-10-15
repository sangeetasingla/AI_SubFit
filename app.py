import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="AI SubFit - Universal School Adjustment", layout="wide")

st.title("⚡ AI SubFit: Smart Timetable Adjustment System")
st.caption("Universal Solution for Government & Private Schools (Auto-Load Master Timetable)")

if 'workload_history' not in st.session_state:
    st.session_state.workload_history = {}

# ---------------------------------------------------------
# AUTO-LOAD PERMANENT MASTER TIMETABLE
# ---------------------------------------------------------
df_raw = None
default_file_name = "TT_Fixed.xlsx"

if os.path.exists(default_file_name):
    try:
        df_raw = pd.read_excel(default_file_name)
        st.sidebar.success(f"📂 Master Timetable Auto-Loaded Successfully!")
    except Exception as e:
        st.sidebar.warning(f"⚠️ Auto-load failed: {e}")

# If default file not found, allow manual upload
st.sidebar.header("📁 Timetable Management")
uploaded_file = st.sidebar.file_uploader("Upload / Update Master Timetable (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)
    st.sidebar.success("✅ New Timetable Uploaded!")

if df_raw is not None:
    # Strip spaces from column names
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    columns = list(df_raw.columns)

    # Day Column Detection
    day_cols = [col for col in columns if "day" in str(col).lower()]
    has_day_col = len(day_cols) > 0

    selected_day = st.sidebar.selectbox(
        "📅 Select Working Day:",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    )

    # Filter strictly by selected day if Day column exists
    if has_day_col:
        day_col_name = day_cols[0]
        day_prefix = selected_day[:3].lower()
        df = df_raw[df_raw[day_col_name].astype(str).str.strip().str.lower().str.startswith(day_prefix)].copy()

        if df.empty:
            df = df_raw.copy()
            teacher_col = columns[0]
            period_cols = columns[1:]
        else:
            teacher_col = [col for col in columns if col != day_col_name][0]
            period_cols = [col for col in columns if col not in [day_col_name, teacher_col]]
    else:
        df = df_raw.copy()
        teacher_col = columns[0]
        period_cols = columns[1:]

    all_teachers = sorted([str(t).strip() for t in df[teacher_col].dropna().unique().tolist() if str(t).strip() != ""])

    for t in all_teachers:
        if t not in st.session_state.workload_history:
            st.session_state.workload_history[t] = 0

    st.divider()

    # Step 1: Absent Teacher Selection
    st.subheader(f"📌 Step 1: Select Absent Teachers ({selected_day})")
    absent_teachers = st.multiselect("Select Absent Teacher(s):", options=all_teachers)

    # Step 2: Per-Teacher Leave Type
    teacher_leave_config = {}
    total_periods_count = len(period_cols)
    half_mark = total_periods_count // 2

    if absent_teachers:
        st.subheader("⚙️ Step 2: Configure Leave Type for Each Teacher")
        for abs_t in absent_teachers:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"**{abs_t}**")
            with col2:
                l_type = st.radio(
                    f"Leave Type for {abs_t}",
                    ["Full Day", "First Half", "Second Half"],
                    horizontal=True,
                    key=f"leave_{abs_t}"
                )

            if l_type == "Full Day":
                teacher_leave_config[abs_t] = period_cols
            elif l_type == "First Half":
                teacher_leave_config[abs_t] = period_cols[:half_mark]
            else:
                teacher_leave_config[abs_t] = period_cols[half_mark:]

    st.divider()

    # Step 3: Generate Adjustment
    if absent_teachers and st.button("🚀 GENERATE SMART ADJUSTMENT PLAN", type="primary"):
        st.subheader(f"📋 Generated Substitution List ({selected_day})")

        adjustments = []

        for period in period_cols:
            for abs_teacher in absent_teachers:
                if period not in teacher_leave_config[abs_teacher]:
                    continue

                t_row = df[df[teacher_col].astype(str).str.strip() == abs_teacher]

                if not t_row.empty:
                    val = t_row[period].values[0]
                    raw_val = str(val).strip() if pd.notna(val) else ""
                    val_lower = raw_val.lower()

                    is_empty_or_free = (
                        pd.isna(val) or
                        raw_val == "" or
                        val_lower in ["nan", "none", "free", "off", "-", "null", "nil", "0", "0.0"] or
                        len(raw_val) < 2
                    )

                    if not is_empty_or_free:
                        free_teachers = []
                        for t_name in all_teachers:
                            if t_name in absent_teachers:
                                continue

                            sub_row = df[df[teacher_col].astype(str).str.strip() == t_name]
                            if not sub_row.empty:
                                sub_val = sub_row[period].values[0]
                                sub_raw = str(sub_val).strip() if pd.notna(sub_val) else ""
                                sub_lower = sub_raw.lower()

                                if pd.isna(sub_val) or sub_raw == "" or sub_lower in ["nan", "none", "free", "off", "-", "null", "nil", "0", "0.0"] or len(sub_raw) < 2:
                                    free_teachers.append(t_name)

                        if free_teachers:
                            free_teachers.sort(key=lambda t: st.session_state.workload_history.get(t, 0))
                            assigned_sub = free_teachers[0]

                            st.session_state.workload_history[assigned_sub] += 1
                            duty_num = st.session_state.workload_history[assigned_sub]

                            adjustments.append({
                                "Day": selected_day,
                                "Period": period,
                                "Class/Room": raw_val,
                                "Absent Teacher": abs_teacher,
                                "Assigned Substitute": assigned_sub,
                                "Total Duties Today": f"{duty_num} Duty(ies)",
                                "Status": "Assigned ✅"
                            })
                        else:
                            adjustments.append({
                                "Day": selected_day,
                                "Period": period,
                                "Class/Room": raw_val,
                                "Absent Teacher": abs_teacher,
                                "Assigned Substitute": "⚠️ NO FREE TEACHER",
                                "Total Duties Today": "-",
                                "Status": "Alert ❌"
                            })

        if adjustments:
            adj_df = pd.DataFrame(adjustments)
            st.dataframe(adj_df, use_container_width=True)

            with st.expander("📊 View Teacher Workload Tracker"):
                workload_df = pd.DataFrame(
                    list(st.session_state.workload_history.items()),
                    columns=["Teacher Name", "Substitutions Assigned"]
                )
                st.dataframe(workload_df[workload_df["Substitutions Assigned"] > 0])

            st.divider()
            st.subheader("📲 Instant WhatsApp Share")
            wa_text = f"*AI SubFit - {selected_day} Substitution Report*%0A%0A"
            for item in adjustments:
                wa_text += f"• *Period {item['Period']}* ({item['Class/Room']}): {item['Absent Teacher']} ➡️ *{item['Assigned Substitute']}*%0A"

            whatsapp_url = f"https://api.whatsapp.com/send?text={wa_text}"
            st.markdown(
                f'<a href="{whatsapp_url}" target="_blank">'
                f'<button style="background-color:#25D366;color:white;border:none;padding:12px 24px;border-radius:6px;font-weight:bold;cursor:pointer;font-size:16px;">'
                f'💬 Share Complete Report on WhatsApp</button></a>',
                unsafe_allow_html=True
            )
        else:
            st.info(f"Selected absent teacher(s) have NO scheduled classes on {selected_day} during their active leave periods.")

else:
    st.info("⚠️ Master timetable file (TT_Fixed.xlsx) not found in folder. Please upload it using the sidebar.")