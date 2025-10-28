import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import re
import base64
import os
import shutil
# === CONFIG ===
DATABASE = 'school.db'
IMAGE_PATH = r"C:\Users\USER\Desktop\sms"
PHOTO_FOLDER = 'student_photos'
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
def is_valid_name_part(name): return bool(name.strip() and len(name.strip()) >= 1 and all(c.isalpha() or c.isspace() for c in name.strip()))
def is_valid_class(class_name): return bool(class_name.strip())
def is_valid_subject(subject): return bool(subject.strip() and len(subject.strip()) >= 2)
def is_valid_date(dob, max_years=18):
    today = datetime.now().date()
    min_date = today.replace(year=today.year - max_years)
    return min_date <= dob <= today if dob else False
def is_valid_day(day): return day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
def is_valid_period(period): return 1 <= period <= 8
def is_valid_username(username): return bool(username.strip() and len(username.strip()) >= 3 and username.isalnum())
def is_valid_password(password): return bool(password.strip() and len(password.strip()) >= 6)
def is_valid_role(role): return role in ["admin", "headteacher", "teacher"]
def is_valid_activity(activity): return bool(activity.strip() and len(activity.strip()) >= 2)
def is_valid_insurance_number(ins): return bool(ins.strip() and len(ins.strip()) >= 5)
# === DB INIT ===
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Drop old students table if exists to recreate with new schema (for migration; in prod, use ALTER)
    cursor.execute("DROP TABLE IF EXISTS students")
    cursor.execute("DROP TABLE IF EXISTS attendance")
    cursor.execute("DROP TABLE IF EXISTS results")
    cursor.execute("DROP TABLE IF EXISTS fees")
    tables = [
        ("users", "username TEXT PRIMARY KEY, password TEXT NOT NULL, role TEXT NOT NULL"),
        ("students", "first_name TEXT PRIMARY KEY, middle_name TEXT, surname TEXT NOT NULL, class TEXT NOT NULL, dob DATE NOT NULL, gender TEXT NOT NULL, residence TEXT NOT NULL, guardian_name TEXT, guardian_phone TEXT, insurance_number TEXT, registration_date DATE DEFAULT CURRENT_DATE, has_medical_condition BOOLEAN DEFAULT 0, medical_details TEXT, passport_picture_path TEXT"),
        ("teachers", "id INTEGER PRIMARY KEY, name TEXT NOT NULL, subject TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL"),
        ("non_teaching", "id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL"),
        ("attendance", "date DATE NOT NULL, student_first_name TEXT NOT NULL, present BOOLEAN NOT NULL, PRIMARY KEY (date, student_first_name), FOREIGN KEY (student_first_name) REFERENCES students(first_name)"),
        ("results", "student_first_name TEXT NOT NULL, subject TEXT NOT NULL, score INTEGER NOT NULL, PRIMARY KEY (student_first_name, subject), FOREIGN KEY (student_first_name) REFERENCES students(first_name)"),
        ("salary", "teacher_id INTEGER NOT NULL, month TEXT NOT NULL, amount REAL NOT NULL, paid BOOLEAN NOT NULL, PRIMARY KEY (teacher_id, month), FOREIGN KEY (teacher_id) REFERENCES teachers(id)"),
        ("fees", "class TEXT NOT NULL, fee_amount REAL NOT NULL, student_first_name TEXT, paid_amount REAL DEFAULT 0, date_paid DATE, collected_by TEXT, PRIMARY KEY (class, student_first_name), FOREIGN KEY (student_first_name) REFERENCES students(first_name)"),
        ("reports", "teacher_id INTEGER NOT NULL, report_content TEXT NOT NULL, date DATE NOT NULL, PRIMARY KEY (teacher_id, date), FOREIGN KEY (teacher_id) REFERENCES teachers(id)"),
        ("register", "teacher_id INTEGER NOT NULL, class TEXT NOT NULL, date DATE NOT NULL, marked BOOLEAN NOT NULL, PRIMARY KEY (teacher_id, class, date), FOREIGN KEY (teacher_id) REFERENCES teachers(id)"),
        ("class_teachers", "class TEXT NOT NULL, teacher_id INTEGER NOT NULL, PRIMARY KEY (class, teacher_id), FOREIGN KEY (teacher_id) REFERENCES teachers(id)"),
        ("teacher_attendance", "date DATE NOT NULL, teacher_id INTEGER NOT NULL, present BOOLEAN NOT NULL, PRIMARY KEY (date, teacher_id), FOREIGN KEY (teacher_id) REFERENCES teachers(id)"),
        ("timetables", "id INTEGER PRIMARY KEY, class TEXT NOT NULL, day TEXT NOT NULL, period INTEGER NOT NULL, subject TEXT NOT NULL, teacher_id INTEGER, FOREIGN KEY (teacher_id) REFERENCES teachers(id), UNIQUE(class, day, period)"),
        ("subject_assignments", "id INTEGER PRIMARY KEY, class TEXT NOT NULL, subject TEXT NOT NULL, teacher_id INTEGER NOT NULL, FOREIGN KEY (teacher_id) REFERENCES teachers(id), UNIQUE(class, subject)"),
        ("login_logs", "id INTEGER PRIMARY KEY, username TEXT NOT NULL, login_time DATETIME NOT NULL, ip_address TEXT"),
        ("activities", "id INTEGER PRIMARY KEY, activity TEXT NOT NULL, date DATE NOT NULL, description TEXT, UNIQUE(date, activity)")
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
    # Create photo folder
    os.makedirs(PHOTO_FOLDER, exist_ok=True)
    conn.commit()
    conn.close()
# === DATA LOADER ===
def load_data(table):
    try:
        conn = sqlite3.connect(DATABASE)
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        conn.close()
        if table == 'students':
            # Add computed full name for display
            df['full_name'] = df['first_name'] + ' ' + df['middle_name'].fillna('') + ' ' + df['surname']
        return df
    except: return pd.DataFrame()
def generate_id(table):
    if table == 'students':
        return None  # No longer needed
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
        # Log login (basic, no IP for now)
        if result:
            log_id = generate_id('login_logs')
            cursor.execute("INSERT INTO login_logs (id, username, login_time) VALUES (?, ?, ?)",
                           (log_id, username, datetime.now()))
            conn.commit()
        conn.close()
        return result[0] if result else None
    except: return None
# === SEARCH PROFILES ===
def search_profiles(search_query):
    students = load_data('students')
    teachers = load_data('teachers')
   
    student_results = pd.DataFrame()
    teacher_results = pd.DataFrame()
   
    # For students, search by exact first_name or contains full_name
    if not students.empty:
        if search_query in students['first_name'].values:
            student_results = students[students['first_name'] == search_query][['first_name', 'full_name', 'class', 'dob', 'gender', 'residence']]
        else:
            student_results = students[students['full_name'].str.contains(search_query, case=False, na=False)][['first_name', 'full_name', 'class', 'dob', 'gender', 'residence']]
    if not teachers.empty:
        try:
            search_id = int(search_query)
            teacher_results = teachers[teachers['id'] == search_id][['id', 'name', 'subject', 'email', 'phone']]
        except ValueError:
            teacher_results = teachers[teachers['name'].str.contains(search_query, case=False, na=False)][['id', 'name', 'subject', 'email', 'phone']]
   
    return student_results, teacher_results
# === TIMETABLE UTILITIES ===
def get_available_teachers_for_subject(subject, class_name):
    teachers = load_data('teachers')
    assignments = load_data('subject_assignments')
   
    if not teachers.empty:
        available_teachers = teachers[teachers['subject'] == subject]
        if not assignments.empty:
            assigned = assignments[(assignments['class'] == class_name) & (assignments['subject'] == subject)]['teacher_id'].tolist()
            available_teachers = available_teachers[~available_teachers['id'].isin(assigned)]
        return available_teachers[['id', 'name']].to_dict('records')
    return []
def check_conflict(class_name, day, period, teacher_id):
    timetable = load_data('timetables')
    if not timetable.empty and teacher_id:
        conflicts = timetable[
            (timetable['day'] == day) &
            (timetable['period'] == period) &
            (timetable['teacher_id'] == teacher_id) &
            (timetable['class'] != class_name)
        ]
        return not conflicts.empty
    return False
# === VIEW TIMETABLE ===
def view_timetable():
    timetable = load_data('timetables')
    if not timetable.empty:
        st.markdown("<h3 style='color:#ffd700;'>School Timetable</h3>", unsafe_allow_html=True)
        st.dataframe(timetable)
    else:
        st.info("No timetable records available")
# === ACTIVITIES FUNCTIONS ===
def display_activities(role='view'):
    activities = load_data('activities')
    if not activities.empty:
        activities['date'] = pd.to_datetime(activities['date']).dt.date
        st.markdown("<h4 style='color:#ffd700;'>Weekly Activities</h4>", unsafe_allow_html=True)
        st.dataframe(activities.sort_values('date', ascending=False))
        if role == 'headteacher':
            return activities
    else:
        st.info("No activities scheduled yet")
        return pd.DataFrame()
def headteacher_manage_activities():
    tab1, tab2, tab3 = st.tabs(["Add Activity", "Update Activity", "View Activities"])
   
    with tab1:
        st.markdown("<h3 style='color:#ffd700;'>Add Weekly Activity</h3>", unsafe_allow_html=True)
        activity = st.text_input("Activity Name", key="add_activity_name")
        date = st.date_input("Date", key="add_activity_date")
        description = st.text_area("Description", key="add_activity_desc")
        if st.button("Add Activity", key="add_activity_btn"):
            if not is_valid_activity(activity):
                st.error("Invalid activity name")
            else:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                new_id = generate_id('activities')
                try:
                    cursor.execute("INSERT INTO activities VALUES (?, ?, ?, ?)",
                                 (new_id, activity.strip(), date, description.strip() if description else None))
                    conn.commit()
                    st.success("Activity added")
                except sqlite3.IntegrityError:
                    st.error("Activity for this date already exists")
                conn.close()
   
    with tab2:
        st.markdown("<h3 style='color:#ffd700;'>Update Activity</h3>", unsafe_allow_html=True)
        activities = load_data('activities')
        if not activities.empty:
            activity_id = st.number_input("Activity ID", min_value=1, step=1, key="update_activity_id")
            if activity_id in activities['id'].values:
                act = activities[activities['id'] == activity_id].iloc[0]
                new_activity = st.text_input("Activity Name", value=act['activity'], key="update_activity_name")
                new_date = st.date_input("Date", value=pd.to_datetime(act['date']).date(), key="update_activity_date")
                new_desc = st.text_area("Description", value=act['description'] if pd.notna(act['description']) else "", key="update_activity_desc")
                if st.button("Update Activity", key="update_activity_btn"):
                    if not is_valid_activity(new_activity):
                        st.error("Invalid activity name")
                    else:
                        conn = sqlite3.connect(DATABASE)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE activities SET activity=?, date=?, description=? WHERE id=?",
                                     (new_activity.strip(), new_date, new_desc.strip() if new_desc else None, activity_id))
                        conn.commit()
                        conn.close()
                        st.success("Activity updated")
            else:
                st.warning("Activity ID not found")
        else:
            st.info("No activities to update")
   
    with tab3:
        display_activities('headteacher')
# === MAIN ===
def main():
    init_db()
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = True
    def toggle_dark_mode():
        st.session_state.dark_mode = not st.session_state.dark_mode
    photo1_base64 = get_base64_image(os.path.join(IMAGE_PATH, "photo1.jpeg"))
    dark_mode = st.session_state.dark_mode
    bg_gradient = "linear-gradient(135deg, #1a1a1a, #2b1a00, #331c00)" if dark_mode else "linear-gradient(135deg, #f5e6c8, #e6d7a8, #d4c28a)"
    text_color = "#f5e6c8" if dark_mode else "#1a1a1a"
    card_bg = "rgba(255, 215, 0, 0.12)" if dark_mode else "rgba(255, 215, 0, 0.18)"
    card_border = "rgba(255, 215, 0, 0.3)" if dark_mode else "rgba(255, 215, 0, 0.4)"
    input_bg = "#000000"
    input_border = "rgba(255,215,0,0.4)" if dark_mode else "rgba(184,134,11,0.5)"
    table_bg = "rgba(255,215,0,0.05)" if dark_mode else "rgba(255,215,0,0.1)"
    table_head_bg = "rgba(255,215,0,0.25)" if dark_mode else "rgba(255,215,0,0.35)"
    label_color = "#ffd700"
    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            html, body, .stApp {{ font-family: 'Inter', sans-serif; }}
            .stApp:not(.logged-in) {{
                background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)),
                            url("data:image/jpeg;base64,{photo1_base64}") center/cover no-repeat;
                min-height: 100vh;
            }}
            .stApp {{
                background: {bg_gradient};
                min-height: 100vh;
                color: {text_color};
                padding: 1rem;
                transition: background 0.5s ease;
            }}
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
            .magic-box-grid {{
                display: flex;
                flex-direction: row;
                gap: 0.75rem;
                margin: 1rem 0;
                justify-content: flex-start;
                overflow-x: auto;
                padding-bottom: 0.5rem;
            }}
            .magic-box-tile {{
                background: rgba(255, 215, 0, 0.15);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border-radius: 12px;
                padding: 0.8rem;
                text-align: center;
                border: 1px solid rgba(255, 215, 0, 0.3);
                width: 100%;
                max-width: 150px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3), 0 0 10px rgba(255, 215, 0, 0.2);
            }}
            .magic-box-tile:hover {{
                background: rgba(255, 215, 0, 0.25);
                transform: scale(1.05);
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5), 0 0 15px rgba(255, 215, 0, 0.4);
                border-color: rgba(255, 215, 0, 0.5);
            }}
            .magic-box-icon {{ font-size: 1.5rem; margin-bottom: 0.4rem; color: #ffd700; text-shadow: 0 0 8px rgba(255,215,0,0.6); }}
            .magic-box-label {{ font-size: 0.8rem; opacity: 0.9; margin-bottom: 0.3rem; color: {text_color}; font-weight: 500; }}
            .magic-box-value {{ font-size: 1.4rem; font-weight: 700; color: #ffffff; text-shadow: 0 0 10px rgba(255,215,0,0.5); }}
            .section-header {{ font-size: 1.9rem; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 0.7rem; margin-bottom: 1.2rem; text-shadow: 0 0 10px rgba(255,215,0,0.3); }}
            .section-header i {{ color: #ffd700; font-size: 2rem; filter: drop-shadow(0 0 8px rgba(255,215,0,0.5)); }}
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
            .stTabs [data-baseweb="tab"] {{
                background: rgba(255, 215, 0, 0.15);
                color: {text_color};
                border-radius: 12px 12px 0 0;
                margin-right: 6px;
                font-weight: 600;
                border: 1px solid rgba(255,215,0,0.3);
            }}
            .stTabs [data-baseweb="tab"][aria-selected="true"] {{
                background: rgba(255, 215, 0, 0.35);
                color: white;
                border-bottom: none;
                box-shadow: 0 -2px 10px rgba(255,215,0,0.3);
            }}
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
            .stDataFrame {{
                background: {table_bg};
                border-radius: 14px;
                overflow: hidden;
                border: 1px solid rgba(255,215,0,0.2);
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
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea,
            .stSelectbox > div > div > div,
            .stNumberInput > div > div > input {{
                background: {input_bg} !important;
                color: #f5e6c8 !important;
                border: 1.5px solid {input_border} !important;
                border-radius: 10px !important;
            }}
            .stTextInput > div > div > input:focus,
            .stTextArea > div > div > textarea:focus,
            .stNumberInput > div > div > input:focus,
            .stSelectbox > div > div > div:focus {{
                border-color: #ffd700 !important;
                box-shadow: 0 0 15px rgba(255,215,0,0.3) !important;
            }}
            .stTextInput > label,
            .stTextArea > label,
            .stSelectbox > label,
            .stNumberInput > label,
            .stCheckbox > label,
            .stMultiselect > label,
            .stDateInput > label {{
                color: {label_color} !important;
                font-weight: 500 !important;
                text-shadow: 0 0 5px rgba(255,215,0,0.3) !important;
            }}
            .stSuccess {{ background: rgba(255,215,0,0.2); color: white; border: 1px solid #ffd700; border-radius: 8px; }}
            .stError {{ background: rgba(220,20,60,0.3); color: white; border: 1px solid #ff6b6b; border-radius: 8px; }}
            .stWarning {{ background: rgba(255,165,0,0.2); color: white; border: 1px solid #ffa500; border-radius: 8px; }}
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
            .search-bar-container {{
                display: flex;
                align-items: center;
                gap: 1rem;
                margin-bottom: 1rem;
            }}
            .search-bar-container .stTextInput {{
                flex: 1;
                max-width: 500px;
            }}
        </style>
    """, unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center; color:#ffd700; text-shadow: 0 0 20px rgba(255,215,0,0.5);'>D.O Buadu Educational Complex</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; color:#f5e6c8;'>School Management System</h3>", unsafe_allow_html=True)
    toggle_label = "Light Mode" if dark_mode else "Dark Mode"
    toggle_icon = "moon" if dark_mode else "sun"
    st.markdown(f'''
        <div class="dark-mode-toggle" onclick="document.getElementById('toggle-btn').click();">
            <i class="fas fa-{toggle_icon}"></i> {toggle_label}
        </div>
    ''', unsafe_allow_html=True)
    if st.button("", key="toggle-btn", on_click=toggle_dark_mode):
        pass
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
                    st.session_state.username = username # Store for self-delete check
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        st.sidebar.image(os.path.join(IMAGE_PATH, "logo.jpeg"), use_container_width=True, caption="D.O Buadu")
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='color:#ffd700; text-align:center;'>Navigation</h3>", unsafe_allow_html=True)
        def dashboard_page(title, icon, content_func):
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(f'<h2 class="section-header"><i class="fas fa-{icon}"></i> {title}</h2>', unsafe_allow_html=True)
            content_func()
            st.markdown('</div>', unsafe_allow_html=True)
        def show_magic_box_stats():
            students = load_data('students')
            teachers = load_data('teachers')
            fees = load_data('fees')
            collected = fees['paid_amount'].sum() if 'paid_amount' in fees.columns and not fees.empty else 0
            arrears = (fees['fee_amount'] - fees['paid_amount'].fillna(0)).sum() if 'fee_amount' in fees.columns and 'paid_amount' in fees.columns and not fees.empty else 0
            st.markdown('<div class="search-bar-container">', unsafe_allow_html=True)
            search_query = st.text_input("Search Student or Teacher (First Name or Name)", key="dashboard_search")
            if st.button("Search", key="dashboard_search_btn"):
                if search_query:
                    student_results, teacher_results = search_profiles(search_query)
                    if not student_results.empty:
                        st.markdown("<h3 style='color:#ffd700;'>Student Profiles</h3>", unsafe_allow_html=True)
                        st.dataframe(student_results)
                    if not teacher_results.empty:
                        st.markdown("<h3 style='color:#ffd700;'>Teacher Profiles</h3>", unsafe_allow_html=True)
                        st.dataframe(teacher_results)
                    if student_results.empty and teacher_results.empty:
                        st.warning("No matching profiles found")
                else:
                    st.error("Please enter a search query")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="magic-box-grid">', unsafe_allow_html=True)
            st.markdown(f'''
                <div class="magic-box-tile">
                    <div class="magic-box-icon"><i class="fas fa-user-graduate"></i></div>
                    <div class="magic-box-label">Total Students</div>
                    <div class="magic-box-value">{len(students)}</div>
                </div>
                <div class="magic-box-tile">
                    <div class="magic-box-icon"><i class="fas fa-chalkboard-teacher"></i></div>
                    <div class="magic-box-label">Total Teachers</div>
                    <div class="magic-box-value">{len(teachers)}</div>
                </div>
                <div class="magic-box-tile">
                    <div class="magic-box-icon"><i class="fas fa-hand-holding-usd"></i></div>
                    <div class="magic-box-label">Fees Collected</div>
                    <div class="magic-box-value">GH₵ {collected:,.2f}</div>
                </div>
                <div class="magic-box-tile" style="background: rgba(220,20,60,0.25); border-color: rgba(255,99,71,0.4);">
                    <div class="magic-box-icon"><i class="fas fa-exclamation-triangle"></i></div>
                    <div class="magic-box-label">Total Arrears</div>
                    <div class="magic-box-value">GH₵ {arrears:,.2f}</div>
                </div>
            ''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            # Display Activities on Dashboard (read-only for non-headteacher)
            display_activities(st.session_state.role)
        # === USER ACCOUNT MANAGEMENT ===
        def admin_user_accounts():
            tab1, tab2 = st.tabs(["Add User", "Delete User"])
            with tab1:
                st.markdown("<h3 style='color:#ffd700;'>Add User Account</h3>", unsafe_allow_html=True)
                username = st.text_input("Username", key="add_user_username")
                password = st.text_input("Password", type="password", key="add_user_password")
                role = st.selectbox("Role", ["admin", "headteacher", "teacher"], key="add_user_role")
                if st.button("Add User", key="add_user_button"):
                    if not is_valid_username(username):
                        st.error("Username must be at least 3 characters and alphanumeric")
                    elif not is_valid_password(password):
                        st.error("Password must be at least 6 characters")
                    elif not is_valid_role(role):
                        st.error("Invalid role")
                    else:
                        conn = sqlite3.connect(DATABASE)
                        cursor = conn.cursor()
                        try:
                            cursor.execute("INSERT INTO users VALUES (?, ?, ?)", (username.strip(), password.strip(), role))
                            conn.commit()
                            st.success(f"User {username} added with role {role}")
                        except sqlite3.IntegrityError:
                            st.error("Username already exists")
                        conn.close()
            with tab2:
                st.markdown("<h3 style='color:#ffd700;'>Delete User Account</h3>", unsafe_allow_html=True)
                username = st.text_input("Username", key="delete_user_username")
                if st.button("Delete User", key="delete_user_button"):
                    users = load_data('users')
                    if username not in users['username'].values:
                        st.error("Username not found")
                    elif username == st.session_state.get('username', ''): # Prevent self-deletion
                        st.error("Cannot delete your own account")
                    else:
                        conn = sqlite3.connect(DATABASE)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                        conn.commit()
                        conn.close()
                        st.success(f"User {username} deleted")
        # === TIMETABLE MANAGEMENT ===
        def headteacher_timetable_management():
            tab1, tab2, tab3, tab4 = st.tabs([
                "Prepare Timetable", "Assign Subject Teacher",
                "Update Timetable", "Update Assigned Teacher"
            ])
            with tab1:
                st.markdown("<h3 style='color:#ffd700;'>Prepare Timetable</h3>", unsafe_allow_html=True)
                class_name = st.text_input("Class", key="timetable_class")
                day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], key="timetable_day")
                period = st.number_input("Period (1-8)", min_value=1, max_value=8, step=1, key="timetable_period")
                subject = st.text_input("Subject", key="timetable_subject")
                teachers = load_data('teachers')
                teacher_options = [(t['id'], t['name']) for t in teachers.to_dict('records')] if not teachers.empty else []
                teacher_id = st.selectbox("Teacher (Optional)", ["None"] + [f"{t[1]} (ID: {t[0]})" for t in teacher_options], key="timetable_teacher")
                teacher_id = None if teacher_id == "None" else int(teacher_id.split("ID: ")[1][:-1]) if teacher_id else None
               
                if st.button("Add Slot", key="add_timetable_slot"):
                    if not is_valid_class(class_name):
                        st.error("Invalid class name")
                    elif not is_valid_day(day):
                        st.error("Invalid day")
                    elif not is_valid_period(period):
                        st.error("Period must be between 1 and 8")
                    elif not is_valid_subject(subject):
                        st.error("Invalid subject")
                    elif teacher_id and check_conflict(class_name, day, period, teacher_id):
                        st.error("Teacher is already assigned to another class at this time")
                    else:
                        conn = sqlite3.connect(DATABASE)
                        cursor = conn.cursor()
                        new_id = generate_id('timetables')
                        try:
                            cursor.execute("INSERT INTO timetables VALUES (?, ?, ?, ?, ?, ?)",
                                         (new_id, class_name.strip(), day, period, subject.strip(), teacher_id))
                            conn.commit()
                            st.success("Timetable slot added")
                        except sqlite3.IntegrityError:
                            st.error("This class already has a subject scheduled for this day and period")
                        conn.close()
               
                timetable = load_data('timetables')
                if not timetable.empty:
                    st.markdown("<h4 style='color:#ffd700;'>Current Timetable</h4>", unsafe_allow_html=True)
                    st.dataframe(timetable)
            with tab2:
                st.markdown("<h3 style='color:#ffd700;'>Assign Subject Teacher</h3>", unsafe_allow_html=True)
                class_name = st.text_input("Class", key="assign_class")
                subject = st.text_input("Subject", key="assign_subject")
                teachers = load_data('teachers')
                teacher_options = [(t['id'], t['name']) for t in teachers.to_dict('records')] if not teachers.empty else []
                teacher_id = st.selectbox("Teacher", [f"{t[1]} (ID: {t[0]})" for t in teacher_options], key="assign_teacher")
                teacher_id = int(teacher_id.split("ID: ")[1][:-1]) if teacher_id else None
               
                if st.button("Assign", key="assign_subject_teacher"):
                    if not is_valid_class(class_name):
                        st.error("Invalid class name")
                    elif not is_valid_subject(subject):
                        st.error("Invalid subject")
                    elif not teacher_id:
                        st.error("Please select a teacher")
                    else:
                        conn = sqlite3.connect(DATABASE)
                        cursor = conn.cursor()
                        new_id = generate_id('subject_assignments')
                        try:
                            cursor.execute("INSERT INTO subject_assignments VALUES (?, ?, ?, ?)",
                                         (new_id, class_name.strip(), subject.strip(), teacher_id))
                            conn.commit()
                            st.success("Teacher assigned to subject")
                        except sqlite3.IntegrityError:
                            st.error("This subject is already assigned for this class")
                        conn.close()
               
                assignments = load_data('subject_assignments')
                if not assignments.empty:
                    st.markdown("<h4 style='color:#ffd700;'>Current Assignments</h4>", unsafe_allow_html=True)
                    st.dataframe(assignments)
            with tab3:
                st.markdown("<h3 style='color:#ffd700;'>Update Timetable</h3>", unsafe_allow_html=True)
                timetable = load_data('timetables')
                slot_id = st.number_input("Timetable Slot ID", min_value=1, step=1, key="update_timetable_id")
                if slot_id in timetable['id'].values:
                    slot = timetable[timetable['id'] == slot_id].iloc[0]
                    class_name = st.text_input("Class", value=slot['class'], key="update_timetable_class")
                    day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                                      index=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].index(slot['day']),
                                      key="update_timetable_day")
                    period = st.number_input("Period (1-8)", min_value=1, max_value=8, step=1, value=slot['period'], key="update_timetable_period")
                    subject = st.text_input("Subject", value=slot['subject'], key="update_timetable_subject")
                    teachers = load_data('teachers')
                    teacher_options = [(t['id'], t['name']) for t in teachers.to_dict('records')] if not teachers.empty else []
                    current_teacher = f"{teachers[teachers['id'] == slot['teacher_id']]['name'].values[0]} (ID: {slot['teacher_id']})" if pd.notna(slot['teacher_id']) and not teachers[teachers['id'] == slot['teacher_id']].empty else "None"
                    teacher_id = st.selectbox("Teacher (Optional)", ["None"] + [f"{t[1]} (ID: {t[0]})" for t in teacher_options],
                                             index=0 if current_teacher == "None" else ([t[1] for t in teacher_options].index(current_teacher.split(" (")[0]) + 1 if current_teacher != "None" else 0),
                                             key="update_timetable_teacher")
                    teacher_id = None if teacher_id == "None" else int(teacher_id.split("ID: ")[1][:-1]) if teacher_id else None
                   
                    if st.button("Update Slot", key="update_timetable_slot"):
                        if not is_valid_class(class_name):
                            st.error("Invalid class name")
                        elif not is_valid_day(day):
                            st.error("Invalid day")
                        elif not is_valid_period(period):
                            st.error("Period must be between 1 and 8")
                        elif not is_valid_subject(subject):
                            st.error("Invalid subject")
                        elif teacher_id and check_conflict(class_name, day, period, teacher_id):
                            st.error("Teacher is already assigned to another class at this time")
                        else:
                            conn = sqlite3.connect(DATABASE)
                            cursor = conn.cursor()
                            try:
                                cursor.execute("UPDATE timetables SET class=?, day=?, period=?, subject=?, teacher_id=? WHERE id=?",
                                             (class_name.strip(), day, period, subject.strip(), teacher_id, slot_id))
                                conn.commit()
                                st.success("Timetable slot updated")
                            except sqlite3.IntegrityError:
                                st.error("This class already has a subject scheduled for this day and period")
                            conn.close()
                else:
                    st.warning("Slot ID not found")
               
                if not timetable.empty:
                    st.markdown("<h4 style='color:#ffd700;'>Current Timetable</h4>", unsafe_allow_html=True)
                    st.dataframe(timetable)
            with tab4:
                st.markdown("<h3 style='color:#ffd700;'>Update Assigned Teacher</h3>", unsafe_allow_html=True)
                assignments = load_data('subject_assignments')
                assignment_id = st.number_input("Assignment ID", min_value=1, step=1, key="update_assignment_id")
                if assignment_id in assignments['id'].values:
                    assignment = assignments[assignments['id'] == assignment_id].iloc[0]
                    class_name = st.text_input("Class", value=assignment['class'], key="update_assignment_class")
                    subject = st.text_input("Subject", value=assignment['subject'], key="update_assignment_subject")
                    teachers = load_data('teachers')
                    teacher_options = [(t['id'], t['name']) for t in teachers.to_dict('records')] if not teachers.empty else []
                    current_teacher = f"{teachers[teachers['id'] == assignment['teacher_id']]['name'].values[0]} (ID: {assignment['teacher_id']})"
                    teacher_id = st.selectbox("Teacher", [f"{t[1]} (ID: {t[0]})" for t in teacher_options],
                                             index=[t[1] for t in teacher_options].index(current_teacher.split(" (")[0]),
                                             key="update_assignment_teacher")
                    teacher_id = int(teacher_id.split("ID: ")[1][:-1]) if teacher_id else None
                   
                    if st.button("Update Assignment", key="update_assignment_teacher_btn"):
                        if not is_valid_class(class_name):
                            st.error("Invalid class name")
                        elif not is_valid_subject(subject):
                            st.error("Invalid subject")
                        elif not teacher_id:
                            st.error("Please select a teacher")
                        else:
                            conn = sqlite3.connect(DATABASE)
                            cursor = conn.cursor()
                            try:
                                cursor.execute("UPDATE subject_assignments SET class=?, subject=?, teacher_id=? WHERE id=?",
                                             (class_name.strip(), subject.strip(), teacher_id, assignment_id))
                                conn.commit()
                                st.success("Teacher assignment updated")
                            except sqlite3.IntegrityError:
                                st.error("This subject is already assigned for this class")
                            conn.close()
                else:
                    st.warning("Assignment ID not found")
               
                if not assignments.empty:
                    st.markdown("<h4 style='color:#ffd700;'>Current Assignments</h4>", unsafe_allow_html=True)
                    st.dataframe(assignments)
        if st.session_state.role == 'admin':
            page = st.sidebar.selectbox("Menu", ["Dashboard", "Students", "Staff", "Fees", "Database", "User Accounts", "View Timetable"], key="admin_menu")
            if page == "Dashboard": dashboard_page("Admin Dashboard", "tachometer-alt", show_magic_box_stats)
            elif page == "Students": dashboard_page("Student Management", "users", admin_students)
            elif page == "Staff": dashboard_page("Staff Management", "user-tie", admin_staff)
            elif page == "Fees": dashboard_page("Fees Management", "money-bill-wave", admin_fees)
            elif page == "Database": dashboard_page("Database Tables", "database", admin_database)
            elif page == "User Accounts": dashboard_page("User Account Management", "user-cog", admin_user_accounts)
            elif page == "View Timetable": dashboard_page("View Timetable", "calendar-alt", view_timetable)
        elif st.session_state.role == 'headteacher':
            page = st.sidebar.selectbox("Menu", [
                "Dashboard", "View Student Profiles", "Check Student Attendance", "Check Student Results",
                "View Teacher Profiles", "Check Teacher Attendance", "Check Registers Marked", "Check Reports",
                "View Fees Records", "Print Fees Report", "Fee Payment", "Add Class",
                "Assign Class Teacher", "Mark Teacher Attendance", "Bulk Teacher Attendance",
                "Bulk Student Attendance", "Bulk Student Attendance by Class", "Reports",
                "Timetable Management", "Manage Weekly Activities"
            ], key="headteacher_menu")
            if page == "Dashboard": dashboard_page("Headteacher Overview", "school", show_magic_box_stats)
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
            elif page == "Timetable Management": dashboard_page("Timetable Management", "calendar-alt", headteacher_timetable_management)
            elif page == "Manage Weekly Activities": dashboard_page("Manage Weekly Activities", "tasks", headteacher_manage_activities)
        elif st.session_state.role == 'teacher':
            page = st.sidebar.selectbox("Menu", ["Teacher Panel", "View Timetable"], key="teacher_menu")
            if page == "Teacher Panel": dashboard_page("Teacher Panel", "chalkboard", teacher_ui)
            elif page == "View Timetable": dashboard_page("View Timetable", "calendar-alt", view_timetable)
            # Display activities read-only for teachers
            display_activities('teacher')
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
        st.markdown("<h3 style='color:#ffd700;'>Add Student</h3>", unsafe_allow_html=True)
        first_name = st.text_input("First Name", key="add_first_name")
        middle_name = st.text_input("Middle Name (Optional)", key="add_middle_name")
        surname = st.text_input("Surname", key="add_surname")
        class_ = st.text_input("Class", key="add_student_class")
        dob = st.date_input("Date of Birth", key="add_student_dob")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="add_student_gender")
        residence = st.text_area("Residence", key="add_residence")
        guardian_name = st.text_input("Guardian Name", key="add_guardian_name")
        guardian_phone = st.text_input("Guardian Phone", key="add_guardian_phone")
        insurance_number = st.text_input("Insurance Number", key="add_insurance")
        has_medical = st.checkbox("Has Medical Condition?", key="add_has_medical")
        medical_details = st.text_area("Medical Details", key="add_medical_details") if has_medical else ""
        uploaded_file = st.file_uploader("Upload Passport Picture (JPG/PNG)", type=['jpg', 'jpeg', 'png'], key="add_photo")
        photo_path = None
        if uploaded_file is not None:
            photo_filename = f"{first_name.strip()}.{uploaded_file.name.split('.')[-1]}"
            photo_path = os.path.join(PHOTO_FOLDER, photo_filename)
            with open(photo_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Photo uploaded: {photo_filename}")
        if st.button("Add Student", key="add_student_button"):
            if not is_valid_name_part(first_name): st.error("Invalid first name")
            elif not is_valid_name_part(surname): st.error("Invalid surname")
            elif not is_valid_class(class_): st.error("Invalid class")
            elif not is_valid_date(dob): st.error("Invalid DOB (must be under 18 years)")
            elif not residence.strip(): st.error("Residence required")
            elif guardian_name and not is_valid_name_part(guardian_name): st.error("Invalid guardian name")
            elif guardian_phone and not is_valid_phone(guardian_phone): st.error("Invalid guardian phone")
            elif insurance_number and not is_valid_insurance_number(insurance_number): st.error("Invalid insurance number")
            elif has_medical and not medical_details.strip(): st.error("Medical details required if condition exists")
            else:
                students = load_data('students')
                if first_name.strip() in students['first_name'].values:
                    st.error("First name already exists (must be unique)")
                else:
                    conn = sqlite3.connect(DATABASE)
                    cursor = conn.cursor()
                    reg_date = datetime.now().date()
                    cursor.execute("""
                        INSERT INTO students
                        (first_name, middle_name, surname, class, dob, gender, residence, guardian_name, guardian_phone,
                         insurance_number, registration_date, has_medical_condition, medical_details, passport_picture_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (first_name.strip(), middle_name.strip() if middle_name else None, surname.strip(),
                          class_.strip(), dob, gender, residence.strip(), guardian_name.strip() if guardian_name else None,
                          guardian_phone.strip() if guardian_phone else None, insurance_number.strip() if insurance_number else None,
                          reg_date, 1 if has_medical else 0, medical_details.strip() if has_medical else None, photo_path))
                    # Auto-create fee row
                    class_fee_data = load_data('fees')
                    class_fee_row = class_fee_data[class_fee_data['class'] == class_]
                    fee_amount = class_fee_row['fee_amount'].values[0] if not class_fee_row.empty else 0.0
                    cursor.execute("INSERT INTO fees (class, fee_amount, student_first_name, paid_amount) VALUES (?, ?, ?, ?)",
                                   (class_.strip(), fee_amount, first_name.strip(), 0.0))
                    conn.commit()
                    conn.close()
                    st.success(f"Student {first_name} {surname} added")
    with tab2:
        student_first_name = st.text_input("Student First Name", key="delete_student_first_name")
        if st.button("Delete", key="delete_student_button"):
            students = load_data('students')
            if student_first_name not in students['first_name'].values:
                st.error("Student not found")
            else:
                # Delete photo if exists
                student = students[students['first_name'] == student_first_name].iloc[0]
                if student['passport_picture_path'] and os.path.exists(student['passport_picture_path']):
                    os.remove(student['passport_picture_path'])
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM students WHERE first_name = ?", (student_first_name,))
                conn.commit()
                conn.close()
                st.success("Student deleted")
    with tab3:
        st.markdown("<h3 style='color:#ffd700;'>Update Student Profile</h3>", unsafe_allow_html=True)
        old_first_name = st.text_input("Student First Name (for selection)", key="update_student_first_name")
        students = load_data('students')
        if old_first_name in students['first_name'].values:
            s = students[students['first_name'] == old_first_name].iloc[0]
            new_first_name = st.text_input("First Name", value=s['first_name'], key="update_first_name")
            middle_name = st.text_input("Middle Name", value=s['middle_name'] if pd.notna(s['middle_name']) else "", key="update_middle_name")
            surname = st.text_input("Surname", value=s['surname'], key="update_surname")
            class_ = st.text_input("Class", value=s['class'], key="update_class")
            dob = st.date_input("DOB", value=pd.to_datetime(s['dob']).date(), key="update_dob")
            gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(s['gender']), key="update_gender")
            residence = st.text_area("Residence", value=s['residence'], key="update_residence")
            guardian_name = st.text_input("Guardian Name", value=s['guardian_name'] if pd.notna(s['guardian_name']) else "", key="update_guardian_name")
            guardian_phone = st.text_input("Guardian Phone", value=s['guardian_phone'] if pd.notna(s['guardian_phone']) else "", key="update_guardian_phone")
            insurance_number = st.text_input("Insurance Number", value=s['insurance_number'] if pd.notna(s['insurance_number']) else "", key="update_insurance")
            has_medical = st.checkbox("Has Medical Condition?", value=bool(s['has_medical_condition']), key="update_has_medical")
            medical_details = st.text_area("Medical Details", value=s['medical_details'] if pd.notna(s['medical_details']) else "", key="update_medical_details") if has_medical else ""
            # Photo update
            current_photo = s['passport_picture_path'] if pd.notna(s['passport_picture_path']) else None
            if current_photo:
                st.image(current_photo, caption="Current Photo", width=100)
            uploaded_file = st.file_uploader("Update Passport Picture (JPG/PNG)", type=['jpg', 'jpeg', 'png'], key="update_photo")
            new_photo_path = current_photo
            rename_photo = False
            if uploaded_file is not None:
                ext = uploaded_file.name.split('.')[-1]
                new_photo_path = os.path.join(PHOTO_FOLDER, f"{new_first_name.strip()}.{ext}")
                with open(new_photo_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("Photo updated")
                rename_photo = True if current_photo and new_first_name != old_first_name else False
            elif new_first_name != old_first_name and current_photo:
                # Rename existing photo if first_name changes
                ext = os.path.basename(current_photo).split('.')[-1]
                new_photo_path = os.path.join(PHOTO_FOLDER, f"{new_first_name.strip()}.{ext}")
                os.rename(current_photo, new_photo_path)
                rename_photo = True
            if st.button("Update", key="update_student_button"):
                if not is_valid_name_part(new_first_name): st.error("Invalid first name")
                elif new_first_name != old_first_name and new_first_name in students['first_name'].values:
                    st.error("New first name already exists")
                elif not is_valid_name_part(surname): st.error("Invalid surname")
                elif not is_valid_class(class_): st.error("Invalid class")
                elif not is_valid_date(dob): st.error("Invalid DOB")
                elif not residence.strip(): st.error("Residence required")
                elif guardian_name and not is_valid_name_part(guardian_name): st.error("Invalid guardian name")
                elif guardian_phone and not is_valid_phone(guardian_phone): st.error("Invalid guardian phone")
                elif insurance_number and not is_valid_insurance_number(insurance_number): st.error("Invalid insurance number")
                elif has_medical and not medical_details.strip(): st.error("Medical details required")
                else:
                    conn = sqlite3.connect(DATABASE)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE students SET first_name=?, middle_name=?, surname=?, class=?, dob=?, gender=?,
                        residence=?, guardian_name=?, guardian_phone=?, insurance_number=?,
                        has_medical_condition=?, medical_details=?, passport_picture_path=?
                        WHERE first_name=?
                    """, (new_first_name.strip(), middle_name.strip() if middle_name else None, surname.strip(),
                          class_.strip(), dob, gender, residence.strip(),
                          guardian_name.strip() if guardian_name else None,
                          guardian_phone.strip() if guardian_phone else None,
                          insurance_number.strip() if insurance_number else None,
                          1 if has_medical else 0, medical_details.strip() if has_medical else None,
                          new_photo_path, old_first_name))
                    # Update foreign keys in other tables if first_name changed
                    if new_first_name != old_first_name:
                        cursor.execute("UPDATE attendance SET student_first_name=? WHERE student_first_name=?", (new_first_name.strip(), old_first_name))
                        cursor.execute("UPDATE results SET student_first_name=? WHERE student_first_name=?", (new_first_name.strip(), old_first_name))
                        cursor.execute("UPDATE fees SET student_first_name=? WHERE student_first_name=?", (new_first_name.strip(), old_first_name))
                    conn.commit()
                    conn.close()
                    st.success("Student updated")
        else:
            st.warning("Student First Name not found")
    with tab4:
        student_first_name = st.text_input("Student First Name", key="check_attendance_first_name")
        if st.button("Check", key="check_attendance_button"):
            att = load_data('attendance')
            filtered = att[att['student_first_name'] == student_first_name]
            st.dataframe(filtered) if not filtered.empty else st.info("No records")
    with tab5:
        student_first_name = st.text_input("Student First Name", key="check_results_first_name")
        if st.button("Check", key="check_results_button"):
            res = load_data('results')
            filtered = res[res['student_first_name'] == student_first_name]
            st.dataframe(filtered) if not filtered.empty else st.info("No results")
    with tab6:
        student_first_name = st.text_input("Student First Name", key="report_card_first_name")
        if st.button("Generate", key="generate_report_button"):
            results_df = load_data('results')
            attendance_df = load_data('attendance')
            student_df = load_data('students')
            if student_first_name in student_df['first_name'].values:
                s = student_df[student_df['first_name'] == student_first_name].iloc[0]
                report = f"Report Card for {s['full_name']}\nClass: {s['class']}\nGuardian: {s['guardian_name']}\nInsurance: {s['insurance_number']}\nMedical: {s['has_medical_condition']} - {s['medical_details']}\n\nResults:\n"
                res = results_df[results_df['student_first_name'] == student_first_name]
                report += res.to_string(index=False) + "\n\nAttendance:\n"
                att = attendance_df[attendance_df['student_first_name'] == student_first_name]
                report += att.to_string(index=False)
                st.download_button("Download", report, f"report_{student_first_name}.txt", key="download_report")
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
            if not is_valid_name_part(name): st.error("Invalid name")
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
    with tab4:
        st.markdown("<h3 style='color:#ffd700;'>Login Tracking</h3>", unsafe_allow_html=True)
        logs = load_data('login_logs')
        if not logs.empty:
            st.dataframe(logs.sort_values('login_time', ascending=False))
        else:
            st.info("No login logs yet")
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
        student_first_name = st.text_input("Student First Name", key="fees_student_first_name")
        amount = st.number_input("Amount", min_value=0.0, step=0.01, key="fees_amount")
        collected_by = st.text_input("Collected By", key="fees_collected_by")
        if st.button("Record", key="record_payment_button"):
            students = load_data('students')
            if student_first_name not in students['first_name'].values:
                st.error("Student not found")
            else:
                class_ = students[students['first_name'] == student_first_name]['class'].values[0]
                fees_data = load_data('fees')
                fee_row = fees_data[(fees_data['class'] == class_) & (fees_data['student_first_name'] == student_first_name)]
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                if fee_row.empty:
                    # Create row if not exists
                    class_fee = fees_data[(fees_data['class'] == class_) & fees_data['student_first_name'].isna()]
                    fee_amount = class_fee['fee_amount'].values[0] if not class_fee.empty else 0
                    cursor.execute("INSERT INTO fees (class, fee_amount, student_first_name, paid_amount, date_paid, collected_by) VALUES (?, ?, ?, ?, ?, ?)",
                                   (class_, fee_amount, student_first_name, amount, datetime.now().date(), collected_by))
                else:
                    current_paid = fee_row['paid_amount'].values[0]
                    cursor.execute("UPDATE fees SET paid_amount = paid_amount + ?, date_paid = ?, collected_by = ? WHERE student_first_name = ? AND class = ?",
                                   (amount, datetime.now().date(), collected_by, student_first_name, class_))
                conn.commit()
                conn.close()
                st.success("Payment recorded")
    with tab2:
        class_ = st.text_input("Class", key="setup_class")
        fee = st.number_input("Fee Amount", min_value=0.0, step=0.01, key="setup_fee")
        if st.button("Set", key="set_fee_button"):
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO fees (class, fee_amount, student_first_name) VALUES (?, ?, NULL)", (class_, fee))
            conn.commit()
            conn.close()
            st.success("Fee set")
    with tab3:
        fees = load_data('fees')
        if not fees.empty:
            fees['arrears'] = fees['fee_amount'] - fees['paid_amount'].fillna(0)
            st.dataframe(fees[['student_first_name', 'paid_amount', 'arrears']])
    with tab4:
        if st.button("Generate", key="generate_fees_report"):
            fees = load_data('fees')
            if not fees.empty:
                fees['arrears'] = fees['fee_amount'] - fees['paid_amount'].fillna(0)
                st.download_button("Download", fees.to_csv(index=False), "fees_report.csv", key="download_fees_report")
# === ADMIN: DATABASE ===
def admin_database():
    tab1, tab2, tab3 = st.tabs(["Students", "Teachers", "Non-Teaching"])
    with tab1: st.dataframe(load_data('students'))
    with tab2: st.dataframe(load_data('teachers'))
    with tab3: st.dataframe(load_data('non_teaching'))
# === HEADTEACHER FUNCTIONS ===
def headteacher_attendance():
    student_first_name = st.text_input("Student First Name", key="ht_check_att_first_name")
    if st.button("Check", key="ht_check_att_btn"):
        att = load_data('attendance')
        filtered = att[att['student_first_name'] == student_first_name]
        st.dataframe(filtered) if not filtered.empty else st.info("No records")
def headteacher_results():
    student_first_name = st.text_input("Student First Name", key="ht_check_res_first_name")
    if st.button("Check", key="ht_check_res_btn"):
        res = load_data('results')
        filtered = res[res['student_first_name'] == student_first_name]
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
        fees['arrears'] = fees['fee_amount'] - fees['paid_amount'].fillna(0)
        st.dataframe(fees)
    else:
        st.info("No records")
def headteacher_print_fees():
    if st.button("Generate Report", key="ht_print_fees_btn"):
        fees = load_data('fees')
        if not fees.empty:
            fees['arrears'] = fees['fee_amount'] - fees['paid_amount'].fillna(0)
            st.download_button("Download", fees.to_csv(index=False), "fees_report_ht.csv", key="ht_download_fees")
def headteacher_fee_payment():
    student_first_name = st.text_input("Student First Name", key="ht_fee_student_first_name")
    amount = st.number_input("Amount", min_value=0.0, step=0.01, key="ht_fee_amount")
    collected_by = st.text_input("Collected By", key="ht_fee_collected")
    if st.button("Record", key="ht_fee_record_btn"):
        students = load_data('students')
        if student_first_name not in students['first_name'].values:
            st.error("Student not found")
            return
        class_ = students[students['first_name'] == student_first_name]['class'].values[0]
        fees_data = load_data('fees')
        fee_row = fees_data[(fees_data['class'] == class_) & (fees_data['student_first_name'] == student_first_name)]
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        if fee_row.empty:
            # Create if not exists
            class_fee = fees_data[(fees_data['class'] == class_) & fees_data['student_first_name'].isna()]
            fee_amount = class_fee['fee_amount'].values[0] if not class_fee.empty else 0
            cursor.execute("INSERT INTO fees (class, fee_amount, student_first_name, paid_amount, date_paid, collected_by) VALUES (?, ?, ?, ?, ?, ?)",
                           (class_, fee_amount, student_first_name, amount, datetime.now().date(), collected_by))
        else:
            current_paid = fee_row['paid_amount'].values[0]
            cursor.execute("UPDATE fees SET paid_amount = ?, date_paid = ?, collected_by = ? WHERE class = ? AND student_first_name = ?",
                           (current_paid + amount, datetime.now().date(), collected_by, class_, student_first_name))
        conn.commit()
        conn.close()
        st.success("Payment recorded")
def headteacher_add_class():
    class_ = st.text_input("Class", key="ht_add_class")
    fee = st.number_input("Fee", min_value=0.0, step=0.01, key="ht_add_fee")
    if st.button("Add", key="ht_add_class_btn"):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO fees (class, fee_amount, student_first_name) VALUES (?, ?, NULL)", (class_, fee))
        conn.commit()
        conn.close()
        st.success("Class fee added")
def headteacher_assign_class():
    class_ = st.text_input("Class", key="ht_assign_class")
    teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="ht_assign_teacher")
    if st.button("Assign", key="ht_assign_btn"):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO class_teachers VALUES (?, ?)", (class_, teacher_id))
            conn.commit()
            st.success("Assigned")
        except sqlite3.IntegrityError:
            st.error("Assignment already exists")
        conn.close()
def headteacher_mark_teacher_attendance():
    teacher_id = st.number_input("Teacher ID", min_value=1, step=1, key="ht_mark_teacher_id")
    present = st.checkbox("Present", key="ht_mark_present")
    if st.button("Mark", key="ht_mark_btn"):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        date = datetime.now().date()
        cursor.execute("INSERT OR IGNORE INTO teacher_attendance VALUES (?, ?, ?)", (date, teacher_id, present))
        conn.commit()
        conn.close()
        st.success("Marked")
def headteacher_bulk_teacher_attendance():
    teachers = load_data('teachers')
    if not teachers.empty:
        teacher_options = [f"{row['name']} (ID: {row['id']})" for _, row in teachers.iterrows()]
        selected = st.multiselect("Select Teachers", teacher_options, key="ht_bulk_teacher_select")
        present = st.checkbox("Present", key="ht_bulk_teacher_present")
        if st.button("Mark All", key="ht_bulk_teacher_btn"):
            if selected:
                selected_ids = [int(s.split("ID: ")[1][:-1]) for s in selected]
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                date = datetime.now().date()
                for tid in selected_ids:
                    cursor.execute("INSERT OR IGNORE INTO teacher_attendance VALUES (?, ?, ?)", (date, tid, present))
                conn.commit()
                conn.close()
                st.success(f"Marked {len(selected_ids)} teachers")
            else:
                st.error("Select at least one teacher")
def headteacher_bulk_student_attendance():
    students = load_data('students')
    if not students.empty:
        student_options = [f"{row['full_name']} (FN: {row['first_name']})" for _, row in students.iterrows()]
        selected = st.multiselect("Select Students", student_options, key="ht_bulk_student_select")
        present = st.checkbox("Present", key="ht_bulk_student_present")
        if st.button("Mark All", key="ht_bulk_student_btn"):
            if selected:
                selected_first_names = [s.split("FN: ")[1][:-1] for s in selected]
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                date = datetime.now().date()
                for fn in selected_first_names:
                    cursor.execute("INSERT OR IGNORE INTO attendance VALUES (?, ?, ?)", (date, fn, present))
                conn.commit()
                conn.close()
                st.success(f"Marked {len(selected_first_names)} students")
            else:
                st.error("Select at least one student")
def headteacher_bulk_class_attendance():
    class_ = st.text_input("Class", key="ht_bulk_class_input")
    present = st.checkbox("Present", key="ht_bulk_class_present")
    if st.button("Mark Class", key="ht_bulk_class_btn"):
        students = load_data('students')
        class_students = students[students['class'] == class_]['first_name'].tolist()
        if class_students:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            date = datetime.now().date()
            for fn in class_students:
                cursor.execute("INSERT OR IGNORE INTO attendance VALUES (?, ?, ?)", (date, fn, present))
            conn.commit()
            conn.close()
            st.success(f"Marked {len(class_students)} students in {class_}")
        else:
            st.error("No students found in class or invalid class")
def headteacher_summary_reports():
    st.markdown("<h3 style='color:#ffd700;'>Attendance Summary</h3>", unsafe_allow_html=True)
    attendance = load_data('attendance')
    students = load_data('students')
    if not attendance.empty and not students.empty:
        today = datetime.now().date()
        today_att = attendance[attendance['date'] == today]
        present_count = today_att[today_att['present'] == True].shape[0]
        total_students = len(students)
        st.metric("Present Students Today", present_count, delta=present_count - total_students)
        st.dataframe(today_att)
    else:
        st.info("No attendance data available")
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
            cursor.execute("INSERT OR IGNORE INTO register VALUES (?, ?, ?, ?)", (teacher_id, class_, date, True))
            conn.commit()
            conn.close()
            st.success("Register marked")
    with tab2:
        teacher_id = st.number_input("Your ID", min_value=1, step=1, key="teacher_report_id")
        report = st.text_area("Report", key="teacher_report_content")
        if st.button("Submit", key="teacher_submit_report_btn"):
            if report.strip():
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                date = datetime.now().date()
                cursor.execute("INSERT INTO reports VALUES (?, ?, ?)", (teacher_id, report.strip(), date))
                conn.commit()
                conn.close()
                st.success("Report submitted")
            else:
                st.error("Report content required")
    with tab3:
        student_first_name = st.text_input("Student First Name", key="teacher_att_student_first_name")
        present = st.checkbox("Present", key="teacher_att_present")
        if st.button("Mark", key="teacher_mark_att_btn"):
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            date = datetime.now().date()
            cursor.execute("INSERT OR IGNORE INTO attendance VALUES (?, ?, ?)", (date, student_first_name, present))
            conn.commit()
            conn.close()
            st.success("Attendance marked")
    with tab4:
        student_first_name = st.text_input("Student First Name", key="teacher_result_student_first_name")
        subject = st.text_input("Subject", key="teacher_result_subject")
        score = st.number_input("Score", min_value=0, max_value=100, step=1, key="teacher_result_score")
        if st.button("Add", key="teacher_add_result_btn"):
            if is_valid_subject(subject):
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO results VALUES (?, ?, ?)", (student_first_name, subject.strip(), score))
                conn.commit()
                conn.close()
                st.success("Result added")
            else:
                st.error("Invalid subject")
if __name__ == "__main__":
    main()