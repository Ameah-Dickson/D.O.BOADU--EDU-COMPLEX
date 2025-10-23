import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import re
import base64
import os

# === CONFIG ===
DATABASE = 'school.db'
IMAGE_PATH = r"C:\Users\USER\Desktop\sms"

# === IMAGE ENCODER ===
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        st.error(f"Error loading image {image_path}: {str(e)}")
        return ""

# === VALIDATION ===
def is_valid_email(email): return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)) if email else False
def is_valid_phone(phone): return bool(re.match(r'^\+?\d{10,15}$', phone)) if phone else False
def is_valid_name(name): return bool(name.strip() and len(name.strip()) >= 2 and all(c.isalpha() or c.isspace() for c in name.strip()))
def is_valid_class(class_name): return bool(class_name.strip())
def is_valid_subject(subject): return bool(subject.strip() and len(subject.strip()) >= 2)
def is_valid_date(dob, max_years=18):
    today = datetime.now().date()
    min_date = today.replace(year=today.year - max_years)
    return min_date <= dob <= today if dob else False

# === DB INIT ===
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    tables = [
        ("users", "username TEXT PRIMARY KEY, password TEXT NOT NULL, role TEXT NOT NULL"),
        ("students", "id INTEGER PRIMARY KEY, name TEXT NOT NULL, class TEXT NOT NULL, dob DATE NOT NULL, gender TEXT NOT NULL, address TEXT NOT NULL"),
        ("teachers", "id INTEGER PRIMARY KEY, name TEXT NOT NULL, subject TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL"),
        ("non_teaching", "id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL"),
        ("attendance", "date DATE NOT NULL, student_id INTEGER NOT NULL, present BOOLEAN NOT NULL, PRIMARY KEY (date, student_id), FOREIGN KEY (student_id) REFERENCES students(id)"),
        ("results", "student_id INTEGER NOT NULL, subject TEXT NOT NULL, score INTEGER NOT NULL, PRIMARY KEY (student_id, subject), FOREIGN KEY (student_id) REFERENCES students(id)"),
        ("salary", "teacher_id INTEGER NOT NULL, month TEXT NOT NULL, amount REAL NOT NULL, paid BOOLEAN NOT NULL, PRIMARY KEY (teacher_id, month), FOREIGN KEY (teacher_id) REFERENCES teachers(id)"),
        ("fees", "class TEXT NOT NULL, fee_amount REAL NOT NULL, student_id INTEGER, paid_amount REAL, date_paid DATE, collected_by TEXT, PRIMARY KEY (class, student_id), FOREIGN KEY (student_id) REFERENCES students(id)"),
        ("reports", "teacher_id INTEGER NOT NULL, report_content TEXT NOT NULL, date DATE NOT NULL, PRIMARY KEY (teacher_id, date), FOREIGN KEY (teacher_id) REFERENCES teachers(id)"),
        ("register", "teacher_id INTEGER NOT NULL, class TEXT NOT NULL, date DATE NOT NULL, marked BOOLEAN NOT NULL, PRIMARY KEY (teacher_id, class, date), FOREIGN KEY (teacher_id) REFERENCES teachers(id)"),
        ("class_teachers", "class TEXT NOT NULL, teacher_id INTEGER NOT NULL, PRIMARY KEY (class, teacher_id), FOREIGN KEY (teacher_id) REFERENCES teachers(id)"),
        ("teacher_attendance", "date DATE NOT NULL, teacher_id INTEGER NOT NULL, present BOOLEAN NOT NULL, PRIMARY KEY (date, teacher_id), FOREIGN KEY (teacher_id) REFERENCES teachers(id)")
    ]
    for table, schema in tables:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({schema})")
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?)", [
            ('admin', 'admin123', 'admin'),
            ('headteacher', 'head123', 'headteacher'),
            ('teacher1', 'teach123', 'teacher')
        ])
    conn.commit()
    conn.close()

# === DATA LOADER ===
def load_data(table):
    try:
        conn = sqlite3.connect(DATABASE)
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

def generate_id(table):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(f"SELECT MAX(id) FROM {table}")
        max_id = cursor.fetchone()[0]
        conn.close()
        return (max_id or 0) + 1
    except: return 1

# === AUTH ===
def authenticate(username, password):
    if not username or not password: return None
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE username = ? AND password = ?", (username, password))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except: return None

# === MAIN ===
def main():
    init_db()

    # === DARK MODE TOGGLE ===
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True  # Default: Dark

    def toggle_dark_mode():
        st.session_state.dark_mode = not st.session_state.dark_mode

    # === CSS WITH DARK MODE ===
    photo1_base64 = get_base64_image(os.path.join(IMAGE_PATH, "photo1.jpeg"))
    dark_mode = st.session_state.dark_mode

    # Dynamic colors
    bg_gradient = "linear-gradient(135deg, #1a1a1a, #2b1a00, #331c00)" if dark_mode else "linear-gradient(135deg, #f5e6c8, #e6d7a8, #d4c28a)"
    text_color = "#f5e6c8" if dark_mode else "#1a1a1a"
    card_bg = "rgba(255, 215, 0, 0.12)" if dark_mode else "rgba(255, 215, 0, 0.18)"
    card_border = "rgba(255, 215, 0, 0.3)" if dark_mode else "rgba(255, 215, 0, 0.4)"
    input_bg = "rgba(255,255,255,0.1)" if dark_mode else "rgba(0,0,0,0.07)"
    input_border = "rgba(255,215,0,0.4)" if dark_mode else "rgba(184,134,11,0.5)"
    metric_tile_bg = "rgba(255, 215, 0, 0.18)" if dark_mode else "rgba(255, 215, 0, 0.25)"
    table_bg = "rgba(255,215,0,0.05)" if dark_mode else "rgba(255,215,0,0.1)"
    table_head_bg = "rgba(255,215,0,0.25)" if dark_mode else "rgba(255,215,0,0.35)"

    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');

            * {{ margin:0; padding:0; box-sizing:border-box; }}
            html, body, .stApp {{ font-family: 'Inter', sans-serif; }}

            /* Login Screen */
            .stApp:not(.logged-in) {{
                background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), 
                            url("data:image/jpeg;base64,{photo1_base64}") center/cover no-repeat;
                min-height: 100vh;
            }}

            /* Dashboard Background */
            .stApp.dashboard {{
                background: {bg_gradient};
                min-height: 100vh;
                color: {text_color};
                padding: 1rem;
                transition: background 0.5s ease;
            }}

            /* Glass Card */
            .glass-card {{
                background: {card_bg};
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);
                border-radius: 18px;
                border: 1.5px solid {card_border};
                padding: 2rem;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(255, 215, 0, 0.15);
                margin: 1rem 0;
                transition: all 0.4s ease;
            }}
            .glass-card:hover {{ 
                transform: translateY(-8px); 
                box-shadow: 0 15px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(255, 215, 0, 0.25);
                border-color: rgba(255, 215, 0, 0.5);
            }}

            /* Metrics */
            .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin: 2rem 0; }}
            .metric-tile {{ background: {metric_tile_bg}; border-radius: 16px; padding: 1.6rem; text-align: center; border: 1.5px solid rgba(255, 215, 0, 0.25); }}
            .metric-tile:hover {{ background: rgba(255, 215, 0, 0.3); transform: translateY(-8px) scale(1.02); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4), 0 0 25px rgba(255, 215, 0, 0.3); }}
            .metric-icon {{ font-size: 2.5rem; margin-bottom: 0.7rem; color: #ffd700; text-shadow: 0 0 10px rgba(255,215,0,0.5); }}
            .metric-label {{ font-size: 1rem; opacity: 0.9; margin-bottom: 0.5rem; color: {text_color}; }}
            .metric-value {{ font-size: 2.6rem; font-weight: 700; color: #ffffff; text-shadow: 0 0 15px rgba(255,215,0,0.4); }}

            /* Headers */
            .section-header {{ font-size: 1.9rem; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 0.7rem; margin-bottom: 1.2rem; text-shadow: 0 0 10px rgba(255,215,0,0.3); }}
            .section-header i {{ color: #ffd700; font-size: 2rem; filter: drop-shadow(0 0 8px rgba(255,215,0,0.5)); }}

            /* Buttons */
            .stButton > button {{ 
                background: linear-gradient(45deg, #b8860b, #ffd700, #b8860b) !important; 
                color: #1a1a1a !important; 
                border: 1.5px solid #ffd700 !important; 
                border-radius: 12px !important; 
                padding: 0.8rem 1.6rem !important; 
                font-weight: 700 !important; 
                font-size: 1rem !important; 
                transition: all 0.4s !important; 
                box-shadow: 0 4px 15px rgba(255,215,0,0.3); 
            }}
            .stButton > button:hover {{ 
                background: linear-gradient(45deg, #cc9900, #ffed4e, #cc9900) !important; 
                transform: translateY(-3px) !important; 
                box-shadow: 0 8px 25px rgba(255,215,0,0.5) !important; 
                border-color: #fff !important; 
            }}

            /* Tabs */
            .stTabs [data-baseweb="tab"] {{ 
                background: rgba(255, 215, 0, 0.15); 
                color: {text_color}; 
                border-radius: 12px 12px 0 0; 
                margin-right: 6px; 
                font-weight: 600; 
                border: 1px solid rgba(255,215,0,0.3); 
            }}
            .stTabs [data-baseweb="tab"][aria-selected="true"] {{ 
                background: rgba(224, 195, 29, 0.35); 
                color: white; 
                border-bottom: none; 
                box-shadow: 0 -2px 10px rgba(255,215,0,0.3); 
            }}

            /* Sidebar */
            .css-1d391kg {{ 
                background: rgba(20, 20, 20, 0.95); 
                backdrop-filter: blur(12px); 
                border-right: 1px solid rgba(255,215,0,0.2); 
            }}
            .sidebar-logo {{ 
                width: 100%; max-width: 170px; margin: 1.8rem auto; 
                border: 3px solid #ffd700; 
                border-radius: 14px;
                box-shadow: 0 6px 20px rgba(255,215,0,0.3), 0 0 15px rgba(0,0,0,0.5);
            }}

            /* Table */
            .stDataFrame {{ 
                background: {table_bg}; 
                border-radius: 14px; 
                overflow: hidden;
                border: 1px solid rgba(20, 20, 18, 0.20);
            }}
            .stDataFrame thead th {{ 
                background: {table_head_bg}; 
                color: white; 
                font-weight: 600;
                border-bottom: 2px solid #ffd700;
            }}
            .stDataFrame tbody td {{ 
                color: {text_color}; 
                border-bottom: 1px solid rgba(255,215,0,0.15);
            }}

            /* Inputs */
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea,
            .stSelectbox > div > div > div,
            .stNumberInput > div > div > input {{
                background: {input_bg} !important;
                color: {text_color} !important;
                border: 1.5px solid {input_border} !important;
                border-radius: 10px !important;
            }}
            .stTextInput > div > div > input:focus,
            .stTextArea > div > div > textarea:focus,
            .stNumberInput > div > div > input:focus {{
                border-color: #ffd700 !important;
                box-shadow: 0 0 15px rgba(255,215,0,0.3) !important;
            }}

            /* Feedback */
            .stSuccess {{ background: rgba(255,215,0,0.2); color: white; border: 1px solid #ffd700; border-radius: 8px; }}
            .stError {{ background: rgba(220,20,60,0.3); color: white; border: 1px solid #ff6b6b; border-radius: 8px; }}
            .stWarning {{ background: rgba(255,165,0,0.2); color: white; border: 1px solid #ffa500; border-radius: 8px; }}

            /* Dark Mode Toggle */
            .dark-mode-toggle {{
                position: fixed;
                top: 1rem;
                right: 1rem;
                z-index: 9999;
                background: rgba(255,215,0,0.2);
                border: 2px solid #ffd700;
                border-radius: 50px;
                padding: 0.5rem 1rem;
                color: #ffd700;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                transition: all 0.3s ease;
            }}
            .dark-mode-toggle:hover {{
                background: #ffd700;
                color: #1a1a1a;
                transform: scale(1.05);
            }}
        </style>
    """, unsafe_allow_html=True)

    # === TITLE ===
    st.markdown("<h1 style='text-align:center; color:#ffd700; text-shadow: 0 0 20px rgba(255,215,0,0.5);'>D.O Buadu Educational Complex</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; color:#f5e6c8;'>School Management System</h3>", unsafe_allow_html=True)

    # === DARK MODE TOGGLE BUTTON ===
    toggle_label = "Light Mode" if dark_mode else "Dark Mode"
    toggle_icon = "moon" if dark_mode else "sun"
    st.markdown(f'''
        <div class="dark-mode-toggle" onclick="document.getElementById('toggle-btn').click();">
            <i class="fas fa-{toggle_icon}"></i> {toggle_label}
        </div>
    ''', unsafe_allow_html=True)
    if st.button("", key="toggle-btn", on_click=toggle_dark_mode):
        pass

    # === LOGIN ===
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h2 style='text-align:center; color:#ffd700;'>Login</h2>", unsafe_allow_html=True)
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", use_container_width=True, key="login_button"):
                role = authenticate(username, password)
                if role:
                    st.session_state.logged_in = True
                    st.session_state.role = role
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        # === SIDEBAR ===
        st.sidebar.image(os.path.join(IMAGE_PATH, "logo.jpeg"), use_container_width=True, caption="D.O Buadu")
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='color:#ffd700; text-align:center;'>Navigation</h3>", unsafe_allow_html=True)

        # === DASHBOARD WRAPPER ===
        def dashboard_page(title, icon, content_func):
            st.markdown('<div class="stApp dashboard">', unsafe_allow_html=True)
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(f'<h2 class="section-header"><i class="fas fa-{icon}"></i> {title}</h2>', unsafe_allow_html=True)
            content_func()
            st.markdown('</div></div>', unsafe_allow_html=True)

        # === METRICS ===
        def show_metrics():
            students = load_data('students')
            teachers = load_data('teachers')
            fees = load_data('fees')
            collected = fees['paid_amount'].sum() if 'paid_amount' in fees.columns and not fees.empty else 0
            arrears = (fees['fee_amount'] - fees['paid_amount']).sum() if 'fee_amount' in fees.columns and 'paid_amount' in fees.columns and not fees.empty else 0

            st.markdown('<div class="metrics-grid">', unsafe_allow_html=True)
            st.markdown(f'''
                <div class="metric-tile">
                    <div class="metric-icon"><i class="fas fa-user-graduate"></i></div>
                    <div class="metric-label">Total Students</div>
                    <div class="metric-value">{len(students)}</div>
                </div>
                <div class="metric-tile">
                    <div class="metric-icon"><i class="fas fa-chalkboard-teacher"></i></div>
                    <div class="metric-label">Total Teachers</div>
                    <div class="metric-value">{len(teachers)}</div>
                </div>
                <div class="metric-tile">
                    <div class="metric-icon"><i class="fas fa-hand-holding-usd"></i></div>
                    <div class="metric-label">Fees Collected</div>
                    <div class="metric-value">GH₵ {collected:,.2f}</div>
                </div>
                <div class="metric-tile" style="background: rgba(220,20,60,0.3); border-color: rgba(255,99,71,0.5);">
                    <div class="metric-icon"><i class="fas fa-exclamation-triangle"></i></div>
                    <div class="metric-label">Total Arrears</div>
                    <div class="metric-value">GH₵ {arrears:,.2f}</div>
                </div>
            ''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # === ADMIN MENU ===
        if st.session_state.role == 'admin':
            page = st.sidebar.selectbox("Menu", ["Dashboard", "Students", "Staff", "Fees", "Database"], key="admin_menu")
            if page == "Dashboard": dashboard_page("Admin Dashboard", "tachometer-alt", show_metrics)
            elif page == "Students": dashboard_page("Student Management", "users", admin_students)
            elif page == "Staff": dashboard_page("Staff Management", "user-tie", admin_staff)
            elif page == "Fees": dashboard_page("Fees Management", "money-bill-wave", admin_fees)
            elif page == "Database": dashboard_page("Database Tables", "database", admin_database)

        # === HEADTEACHER MENU ===
        elif st.session_state.role == 'headteacher':
            page = st.sidebar.selectbox("Menu", [
                "Dashboard", "View Student Profiles", "Check Student Attendance", "Check Student Results",
                "View Teacher Profiles", "Check Teacher Attendance", "Check Registers Marked", "Check Reports",
                "View Fees Records", "Print Fees Report", "Fee Payment", "Add Class",
                "Assign Class Teacher", "Mark Teacher Attendance", "Bulk Teacher Attendance", 
                "Bulk Student Attendance", "Bulk Student Attendance by Class", "Reports"
            ], key="headteacher_menu")
            if page == "Dashboard": dashboard_page("Headteacher Overview", "school", show_metrics)
            elif page == "View Student Profiles": dashboard_page("Student Profiles", "user-graduate", lambda: st.dataframe(load_data('students')))
            elif page == "Check Student Attendance": dashboard_page("Student Attendance", "calendar-check", headteacher_attendance)
            elif page == "Check Student Results": dashboard_page("Student Results", "clipboard-list", headteacher_results)
            elif page == "View Teacher Profiles": dashboard_page("Teacher Profiles", "chalkboard-teacher", lambda: st.dataframe(load_data('teachers')))
            elif page == "Check Teacher Attendance": dashboard_page("Teacher Attendance", "user-clock", headteacher_teacher_attendance)
            elif page == "Check Registers Marked": dashboard_page("Registers Marked", "book", headteacher_registers)
            elif page == "Check Reports": dashboard_page("Teacher Reports", "file-alt", headteacher_reports_tab)
            elif page == "View Fees Records": dashboard_page("Fees Records", "receipt", headteacher_fees_records)
            elif page == "Print Fees Report": dashboard_page("Print Fees Report", "print", headteacher_print_fees)
            elif page == "Fee Payment": dashboard_page("Fee Payment", "money-check-alt", headteacher_fee_payment)
            elif page == "Add Class": dashboard_page("Add Class", "plus-circle", headteacher_add_class)
            elif page == "Assign Class Teacher": dashboard_page("Assign Class Teacher", "user-plus", headteacher_assign_class)
            elif page == "Mark Teacher Attendance": dashboard_page("Mark Teacher Attendance", "user-check", headteacher_mark_teacher_attendance)
            elif page == "Bulk Teacher Attendance": dashboard_page("Bulk Teacher Attendance", "users", headteacher_bulk_teacher_attendance)
            elif page == "Bulk Student Attendance": dashboard_page("Bulk Student Attendance", "users-cog", headteacher_bulk_student_attendance)
            elif page == "Bulk Student Attendance by Class": dashboard_page("Bulk by Class", "layer-group", headteacher_bulk_class_attendance)
            elif page == "Reports": dashboard_page("Summary Reports", "chart-bar", headteacher_summary_reports)

        # === TEACHER MENU ===
        elif st.session_state.role == 'teacher':
            dashboard_page("Teacher Panel", "chalkboard", teacher_ui)

        if st.sidebar.button("Logout", key="logout_button"):
            st.session_state.logged_in = False
            st.rerun()

# === ADMIN: STUDENTS ===
def admin_students():
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Add Student", "Delete Student", "Update Profile", 
        "Check Attendance", "Check Results", "Print Report Card"
    ])

    with tab1:
        name = st.text_input("Name", key="add_student_name")
        class_ = st.text_input("Class", key="add_student_class")
        dob = st.date_input("Date of Birth", key="add_student_dob")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="add_student_gender")
        address = st.text_area("Address", key="add_student_address")
        if st.button("Add", key="add_student_button"):
            if not is_valid_name(name): st.error("Invalid name")
            elif not is_valid_class(class_): st.error("Invalid class")
            elif not is_valid_date(dob): st.error("Invalid DOB")
            elif not address.strip(): st.error("Address required")
            else:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                new_id = generate_id('students')
                cursor.execute("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?)", 
                             (new_id, name.strip(), class_.strip(), dob, gender, address.strip()))
                conn.commit()
                conn.close()
                st.success("Student added")

    with tab2:
        student_id = st.number_input("Student ID", min_value=1, step=1, key="delete_student_id")
        if st.button("Delete", key="delete_student_button"):
            students = load_data('students')
            if student_id not in students['id'].values:
                st.error("Student not found")
            else:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
                conn.commit()
                conn.close()
                st.success("Student deleted")

    with tab3:
        student_id = st.number_input("Student ID", min_value=1, step=1, key="update_student_id")
        students = load_data('students')
        if student_id in students['id'].values:
            s = students[students['id'] == student_id].iloc[0]
            name = st.text_input("Name", value=s['name'], key="update_name")
            class_ = st.text_input("Class", value=s['class'], key="update_class")
            dob = st.date_input("DOB", value=pd.to_datetime(s['dob']).date(), key="update_dob")
            gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(s['gender']), key="update_gender")
            address = st.text_area("Address", value=s['address'], key="update_address")
            if st.button("Update", key="update_student_button"):
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute("UPDATE students SET name=?, class=?, dob=?, gender=?, address=? WHERE id=?", 
                             (name.strip(), class_.strip(), dob, gender, address.strip(), student_id))
                conn.commit()
                conn.close()
                st.success("Updated")

    with tab4:
        student_id = st.number_input("Student ID", min_value=1, step=1, key="check_attendance_id")
        if st.button("Check", key="check_attendance_button"):
            att = load_data('attendance')
            filtered = att[att['student_id'] == student_id]
            st.dataframe(filtered) if not filtered.empty else st.info("No records")

    with tab5:
        student_id = st.number_input("Student ID", min_value=1, step=1, key="check_results_id")
        if st.button("Check", key="check_results_button"):
            res = load_data('results')
            filtered = res[res['student_id'] == student_id]
            st.dataframe(filtered) if not filtered.empty else st.info("No results")

    with tab6:
        student_id = st.number_input("Student ID", min_value=1, step=1, key="report_card_id")
        if st.button("Generate", key="generate_report_button"):
            results = load_data('results')
            attendance = load_data('attendance')
            student = load_data('students')
            if student_id in student['id'].values:
                s = student[student['id'] == student_id].iloc[0]
                report = f"Report Card for {s['name']}\nClass: {s['class']}\n\nResults:\n"
                res = results[results['student_id'] == student_id]
                report += res.to_string(index=False) + "\n\nAttendance:\n"
                att = attendance[attendance['student_id'] == student_id]
                report += att.to_string(index=False)
                st.download_button("Download", report, f"report_{student_id}.txt", key="download_report")

# === ADMIN: STAFF ===
def admin_staff():
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Add Teacher", "Update Profile", "Salary Payment", 
        "Check Attendance", "Check Register", "Check Reports"
    ])

    with tab1:
        name = st.text_input("Name", key="add_teacher_name")
        subject = st.text_input("Subject", key="add_teacher_subject")
        email = st.text_input("Email", key="add_teacher_email")
        phone = st.text_input("Phone", key="add_teacher_phone")
        if st.button("Add", key="add_teacher_button"):
            conn = sqlite3.connect(DATABASE)
            if not is_valid_name(name): st.error("Invalid name")
            elif not is_valid_subject(subject): st.error("Invalid subject")
            elif not is_valid_email(email): st.error("Invalid email")
            elif not is_valid_phone(phone): st.error("Invalid phone")
            else:
                cursor = conn.cursor()
                new_id = generate_id('teachers')
                cursor.execute("INSERT INTO teachers VALUES (?, ?, ?, ?, ?)", 
                             (new_id, name.strip(), subject.strip(), email.strip(), phone.strip()))
                username = name.lower().replace(" ", "")
                cursor.execute("INSERT INTO users VALUES (?, ?, ?)", (username, "default123", "teacher"))
                conn.commit()
                conn.close()
                st.success(f"Added. Login: {username}/default123")

    with tab2:
        teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="update_teacher_id")
        teachers = load_data('teachers')
        if teacher_id in teachers['id'].values:
            t = teachers[teachers['id'] == teacher_id].iloc[0]
            name = st.text_input("Name", value=t['name'], key="edit_teacher_name")
            subject = st.text_input("Subject", value=t['subject'], key="edit_teacher_subject")
            email = st.text_input("Email", value=t['email'], key="edit_teacher_email")
            phone = st.text_input("Phone", value=t['phone'], key="edit_teacher_phone")
            if st.button("Update", key="update_teacher_button"):
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute("UPDATE teachers SET name=?, subject=?, email=?, phone=? WHERE id=?", 
                             (name.strip(), subject.strip(), email.strip(), phone.strip(), teacher_id))
                conn.commit()
                conn.close()
                st.success("Updated")

    with tab3:
        teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="salary_teacher_id")
        month = st.text_input("Month (YYYY-MM)", key="salary_month")
        amount = st.number_input("Amount", min_value=0.0, step=0.01, key="salary_amount")
        if st.button("Pay", key="pay_salary_button"):
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO salary VALUES (?, ?, ?, ?)", (teacher_id, month, amount, True))
            conn.commit()
            conn.close()
            st.success("Salary recorded")

    with tab4: st.write("Login tracking not implemented")
    with tab5:
        teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="check_register_id")
        if st.button("Check", key="check_register_button"):
            reg = load_data('register')
            filtered = reg[reg['teacher_id'] == teacher_id]
            st.dataframe(filtered) if not filtered.empty else st.info("No records")
    with tab6:
        teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="check_reports_id")
        if st.button("Check", key="check_reports_button"):
            rep = load_data('reports')
            filtered = rep[rep['teacher_id'] == teacher_id]
            st.dataframe(filtered) if not filtered.empty else st.info("No reports")

# === ADMIN: FEES ===
def admin_fees():
    tab1, tab2, tab3, tab4 = st.tabs(["Payment", "Setup", "Records", "Report"])
    with tab1:
        student_id = st.number_input("Student ID", min_value=1, step=1, key="fees_student_id")
        amount = st.number_input("Amount", min_value=0.0, step=0.01, key="fees_amount")
        collected_by = st.text_input("Collected By", key="fees_collected_by")
        if st.button("Record", key="record_payment_button"):
            students = load_data('students')
            if student_id not in students['id'].values:
                st.error("Student not found")
            else:
                class_ = students[students['id'] == student_id]['class'].values[0]
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute("UPDATE fees SET paid_amount = paid_amount + ?, date_paid = ?, collected_by = ? WHERE student_id = ? AND class = ?", 
                             (amount, datetime.now().date(), collected_by, student_id, class_))
                conn.commit()
                conn.close()
                st.success("Payment recorded")
    with tab2:
        class_ = st.text_input("Class", key="setup_class")
        fee = st.number_input("Fee Amount", min_value=0.0, step=0.01, key="setup_fee")
        if st.button("Set", key="set_fee_button"):
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO fees (class, fee_amount) VALUES (?, ?)", (class_, fee))
            conn.commit()
            conn.close()
            st.success("Fee set")
    with tab3:
        fees = load_data('fees')
        if not fees.empty:
            fees['arrears'] = fees['fee_amount'] - fees['paid_amount']
            st.dataframe(fees[['student_id', 'paid_amount', 'arrears']])
    with tab4:
        if st.button("Generate", key="generate_fees_report"):
            fees = load_data('fees')
            if not fees.empty:
                fees['arrears'] = fees['fee_amount'] - fees['paid_amount']
                st.download_button("Download", fees.to_csv(index=False), "fees_report.csv", key="download_fees_report")

# === ADMIN: DATABASE ===
def admin_database():
    tab1, tab2, tab3 = st.tabs(["Students", "Teachers", "Non-Teaching"])
    with tab1: st.dataframe(load_data('students'))
    with tab2: st.dataframe(load_data('teachers'))
    with tab3: st.dataframe(load_data('non_teaching'))

# === HEADTEACHER FUNCTIONS ===
def headteacher_attendance():
    student_id = st.number_input("Student ID", min_value=1, step=1, key="ht_check_att_id")
    if st.button("Check", key="ht_check_att_btn"):
        att = load_data('attendance')
        filtered = att[att['student_id'] == student_id]
        st.dataframe(filtered) if not filtered.empty else st.info("No records")

def headteacher_results():
    student_id = st.number_input("Student ID", min_value=1, step=1, key="ht_check_res_id")
    if st.button("Check", key="ht_check_res_btn"):
        res = load_data('results')
        filtered = res[res['student_id'] == student_id]
        st.dataframe(filtered) if not filtered.empty else st.info("No results")

def headteacher_teacher_attendance():
    teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="ht_teacher_att_id")
    if st.button("Check", key="ht_teacher_att_btn"):
        att = load_data('teacher_attendance')
        filtered = att[att['teacher_id'] == teacher_id]
        st.dataframe(filtered) if not filtered.empty else st.info("No records")

def headteacher_registers():
    teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="ht_register_id")
    if st.button("Check", key="ht_register_btn"):
        reg = load_data('register')
        filtered = reg[reg['teacher_id'] == teacher_id]
        st.dataframe(filtered) if not filtered.empty else st.info("No records")

def headteacher_reports_tab():
    teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="ht_reports_id")
    if st.button("Check", key="ht_reports_btn"):
        rep = load_data('reports')
        filtered = rep[rep['teacher_id'] == teacher_id]
        st.dataframe(filtered) if not filtered.empty else st.info("No reports")

def headteacher_fees_records():
    fees = load_data('fees')
    if not fees.empty:
        fees['arrears'] = fees['fee_amount'] - fees['paid_amount']
        st.dataframe(fees)
    else:
        st.info("No records")

def headteacher_print_fees():
    if st.button("Generate Report", key="ht_print_fees_btn"):
        fees = load_data('fees')
        if not fees.empty:
            fees['arrears'] = fees['fee_amount'] - fees['paid_amount']
            st.download_button("Download", fees.to_csv(index=False), "fees_report_ht.csv", key="ht_download_fees")

def headteacher_fee_payment():
    student_id = st.number_input("Student ID", min_value=1, step=1, key="ht_fee_student_id")
    amount = st.number_input("Amount", min_value=0.0, step=0.01, key="ht_fee_amount")
    collected_by = st.text_input("Collected By", key="ht_fee_collected")
    if st.button("Record", key="ht_fee_record_btn"):
        st.success("Recorded")

def headteacher_add_class():
    class_ = st.text_input("Class", key="ht_add_class")
    fee = st.number_input("Fee", min_value=0.0, step=0.01, key="ht_add_fee")
    if st.button("Add", key="ht_add_class_btn"):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO fees (class, fee_amount) VALUES (?, ?)", (class_, fee))
        conn.commit()
        conn.close()
        st.success("Added")

def headteacher_assign_class():
    class_ = st.text_input("Class", key="ht_assign_class")
    teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="ht_assign_teacher")
    if st.button("Assign", key="ht_assign_btn"):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO class_teachers VALUES (?, ?)", (class_, teacher_id))
        conn.commit()
        conn.close()
        st.success("Assigned")

def headteacher_mark_teacher_attendance():
    teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="ht_mark_teacher_id")
    present = st.checkbox("Present", key="ht_mark_present")
    if st.button("Mark", key="ht_mark_btn"):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        date = datetime.now().date()
        cursor.execute("INSERT INTO teacher_attendance VALUES (?, ?, ?)", (date, teacher_id, present))
        conn.commit()
        conn.close()
        st.success("Marked")

def headteacher_bulk_teacher_attendance():
    teachers = load_data('teachers')
    selected = st.multiselect("Teachers", teachers['name'], key="ht_bulk_teacher_select")
    present = st.checkbox("Present", key="ht_bulk_teacher_present")
    if st.button("Mark All", key="ht_bulk_teacher_btn"):
        st.success("Bulk marked")

def headteacher_bulk_student_attendance():
    students = load_data('students')
    selected = st.multiselect("Students", students['name'], key="ht_bulk_student_select")
    present = st.checkbox("Present", key="ht_bulk_student_present")
    if st.button("Mark All", key="ht_bulk_student_btn"):
        st.success("Bulk marked")

def headteacher_bulk_class_attendance():
    class_ = st.text_input("Class", key="ht_bulk_class_input")
    present = st.checkbox("Present", key="ht_bulk_class_present")
    if st.button("Mark Class", key="ht_bulk_class_btn"):
        st.success("Class marked")

def headteacher_summary_reports():
    st.write("Summary reports here")

# === TEACHER UI ===
def teacher_ui():
    tab1, tab2, tab3, tab4 = st.tabs(["Mark Register", "Submit Report", "Mark Attendance", "Add Results"])

    with tab1:
        teacher_id = st.number_input("Your ID", min_value=1, step=1, key="teacher_register_id")
        class_ = st.text_input("Class", key="teacher_register_class")
        if st.button("Mark", key="teacher_mark_register_btn"):
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            date = datetime.now().date()
            cursor.execute("INSERT INTO register VALUES (?, ?, ?, ?)", (teacher_id, class_, date, True))
            conn.commit()
            conn.close()
            st.success("Marked")

    with tab2:
        teacher_id = st.number_input("Your ID", min_value=1, step=1, key="teacher_report_id")
        report = st.text_area("Report", key="teacher_report_content")
        if st.button("Submit", key="teacher_submit_report_btn"):
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            date = datetime.now().date()
            cursor.execute("INSERT INTO reports VALUES (?, ?, ?)", (teacher_id, report, date))
            conn.commit()
            conn.close()
            st.success("Submitted")

    with tab3:
        student_id = st.number_input("Student ID", min_value=1, step=1, key="teacher_att_student_id")
        present = st.checkbox("Present", key="teacher_att_present")
        if st.button("Mark", key="teacher_mark_att_btn"):
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            date = datetime.now().date()
            cursor.execute("INSERT INTO attendance VALUES (?, ?, ?)", (date, student_id, present))
            conn.commit()
            conn.close()
            st.success("Marked")

    with tab4:
        student_id = st.number_input("Student ID", min_value=1, step=1, key="teacher_result_student_id")
        subject = st.text_input("Subject", key="teacher_result_subject")
        score = st.number_input("Score", min_value=0, max_value=100, step=1, key="teacher_result_score")
        if st.button("Add", key="teacher_add_result_btn"):
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO results VALUES (?, ?, ?)", (student_id, subject.strip(), score))
            conn.commit()
            conn.close()
            st.success("Added")

if __name__ == "__main__":
    main()