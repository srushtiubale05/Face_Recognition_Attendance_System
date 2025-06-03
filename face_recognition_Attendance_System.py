import os
import pickle
import numpy as np
import cv2
import face_recognition
import cvzone
import mysql.connector
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk
import cvzone
import numpy as np

# MySQL Configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Ssu@2005",
    "database": "python_project",
}
# Global variables
faceLoc = None
image_path = None
selected_subject = None
encodeListKnown = []
studentIds = []
# ================== NEW FUNCTION TO UPDATE FACE ENCODINGS ==================
def update_face_encodings():
    global encodeListKnown, studentIds

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT student_id, image_path FROM students WHERE image_path IS NOT NULL"
        )
        students = cursor.fetchall()

        new_encodeList = []
        new_studentIds = []

        for student in students:
            if os.path.exists(student["image_path"]):
                try:
                    img = face_recognition.load_image_file(student["image_path"])
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    face_encodings = face_recognition.face_encodings(img)
                    if face_encodings:
                        new_encodeList.append(face_encodings[0])
                        new_studentIds.append(student["student_id"])
                except Exception as e:
                    print(f"Error processing image {student['image_path']}: {e}")

        encodeListKnown = new_encodeList
        studentIds = new_studentIds

        # Save the updated encodings
        with open("EncodeFile.p", "wb") as file:
            pickle.dump([encodeListKnown, studentIds], file)

        print("Face encodings updated successfully!")

    except Exception as e:
        print(f"Error updating encodings: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# ================== IMPROVED REGISTRATION FUNCTION ==================
def register_student():
    name = name_var.get().strip()
    major = major_var.get().strip()
    starting_year = starting_year_var.get().strip()
    # standing = standing_var.get().strip()
    year = year_var.get().strip()
    email = email_var.get().strip()

    if not all([name, major, starting_year, year, email]):
        messagebox.showerror("Error", "All fields must be filled!")
        return
    if not image_path:
        messagebox.showerror("Error", "Please upload a student image!")
        return

    # Generate student ID
    student_id = f"STU{str(int(datetime.now().timestamp()))[-6:]}"
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Check if email already exists
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        if cursor.fetchone():
            messagebox.showerror("Error", "This email is already registered!")
            return

        # Check if student already exists based on name and major
        cursor.execute(
            "SELECT * FROM students WHERE name = %s AND major = %s", (name, major)
        )
        if cursor.fetchone():
            messagebox.showerror("Error", "Student already exists!")
            return

        # Register student
        cursor.execute(
            """
            INSERT INTO students (student_id, name, major, starting_year, year, image_path, email)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
            (student_id, name, major, starting_year, year, image_path, email),
        )

        connection.commit()
        messagebox.showinfo("Success", "Student registered successfully!")

        # Update face encodings after registration
        update_face_encodings()

        # Reset form
        name_var.set("")
        major_var.set("")
        starting_year_var.set("")
        year_var.set("")
        email_var.set("")
        image_label.config(image=None)
        image_label.image = None

    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Database error: {err}")
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error: {e}")
    finally:
        if "connection" in locals() and connection.is_connected():
            cursor.close()
            connection.close()


# ================== IMPROVED IMAGE UPLOAD ==================
def upload_image():
    global image_path
    try:
        file_path = filedialog.askopenfilename(
            title="Select Student Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")],
        )
        if file_path:
            # Validate image
            try:
                img = Image.open(file_path)
                img.verify()
                img = Image.open(file_path)  # Reopen for display

                # Resize and display
                img = img.resize((100, 100))
                img = ImageTk.PhotoImage(img)
                image_label.config(image=img)
                image_label.image = img
                image_path = file_path
            except (IOError, SyntaxError) as e:
                messagebox.showerror("Error", f"Invalid image file: {e}")
                image_path = None
    except Exception as e:
        messagebox.showerror("Error", f"Error selecting image: {e}")


# ================== MAIN ATTENDANCE FUNCTION ==================
selected_subject = None


def on_subject_selected(event):
    global selected_subject
    selected_subject = (
        subject_var.get()
    )  # Update the global variable with selected subject
    print(f"Selected Subject: {selected_subject}")


def run_attendance_system():
    global selected_subject, encodeListKnown, studentIds
    print(
        f"Selected Subject: {selected_subject}"
    )  # Debugging line to check the selected subject

    if not selected_subject or selected_subject == "Select a Subject":
        messagebox.showerror("Error", "Please select a subject first!")
        return

    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Could not open camera!")
        return

    cap.set(3, 640)
    cap.set(4, 480)

    # Load background
    imgBackground = cv2.imread("Resources/background.png")

    # Check if the image was loaded successfully
    if imgBackground is None:
        print("Background image not found, using default background.")
        imgBackground = np.zeros((900, 1300, 3), dtype=np.uint8)

    # Load mode images
    folderModePath = "Resources/Modes"
    modePathList = os.listdir(folderModePath) if os.path.exists(folderModePath) else []
    imgModeList = [
        cv2.imread(os.path.join(folderModePath, path))
        for path in modePathList
        if path.endswith((".png", ".jpg", ".jpeg"))
    ]

    if not imgModeList:
        imgModeList = [np.zeros((633, 414, 3), dtype=np.uint8) for _ in range(4)]
        for i, img in enumerate(imgModeList):
            img[:] = (220, 220, 220)
            cv2.putText(
                img, f"Mode {i}", (150, 300), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 0), 2
            )

    # Load face encodings
    try:
        if os.path.exists("EncodeFile.p"):
            with open("EncodeFile.p", "rb") as file:
                encodeListKnownWithIds = pickle.load(file)
            encodeListKnown, studentIds = encodeListKnownWithIds
        else:
            encodeListKnown, studentIds = [], []
            update_face_encodings()  # Create initial encodings file
    except Exception as e:
        print(f"Error loading encodings: {e}")
        encodeListKnown, studentIds = [], []

    # Attendance system variables
    modeType = 0
    counter = 0
    id = -1
    imgStudent = []
    studentInfo = None
    attendanceMarked = False
    alreadyMarked = False
    showProfileStartTime = 0
    displayDuration = 5
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        while True:
            success, img = cap.read()
            if not success:
                print("Camera error. Trying to reconnect...")
                cap.release()
                time.sleep(2)
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    print("Failed to reconnect to camera.")
                    break
                continue

            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            faceCurFrame = face_recognition.face_locations(imgS)
            encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

            # Update background
            try:
                imgBackground[162 : 162 + 480, 55 : 55 + 640] = img
                imgBackground[44 : 44 + 633, 808 : 808 + 414] = imgModeList[modeType]
            except Exception as e:
                print(f"Error updating background: {e}")

            if faceCurFrame and modeType == 0:
                for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
                    matches = face_recognition.compare_faces(
                        encodeListKnown, encodeFace
                    )
                    faceDis = face_recognition.face_distance(
                        encodeListKnown, encodeFace
                    )

                    if len(faceDis) > 0:
                        matchIndex = np.argmin(faceDis)

                        if (
                            matches[matchIndex] and faceDis[matchIndex] < 0.6
                        ):  # Threshold for recognition
                            y1, x2, y2, x1 = faceLoc
                            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                            bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                            imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)

                            id = studentIds[matchIndex]
                            print(f"Recognized Student ID: {id}")

                            # Get student info
                            cursor.execute(
                                "SELECT * FROM students WHERE student_id = %s", (id,)
                            )
                            studentInfo = cursor.fetchone()
                            if id == -1:
                                cursor.execute(
                                    "INSERT INTO attendance (name, id, status, time) VALUES ('Unknown', NULL, 'Absent', CURRENT_TIMESTAMP)"
                                )

                            elif studentInfo:
                                # Check existing attendance
                                cursor.execute(
                                    """SELECT * FROM attendance WHERE student_id = %s AND subject = %s AND DATE(date_time) = CURDATE()""",
                                    (id, selected_subject),
                                )

                                if cursor.fetchone():
                                    print("Attendance already marked today.")
                                    alreadyMarked = True
                                    attendanceMarked = False
                                else:
                                    # Mark attendance
                                    current_time = datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    )
                                    current_date = datetime.now().strftime("%Y-%m-%d")
                                    # Insert into attendance table
                                    cursor.execute(
                                        """INSERT INTO attendance (student_id, subject, date_time, attendance_date) VALUES (%s, %s, %s, %s)""",
                                        (
                                            id,
                                            selected_subject,
                                            current_time,
                                            current_date,
                                        ),
                                    )
                                    # Update subject attendance
                                    cursor.execute(
                                        """INSERT INTO subject_attendance (student_id, subject, attendance_count, last_attendance_time) VALUES (%s, %s, 1, %s) ON DUPLICATE KEY UPDATE attendance_count = attendance_count + 1, last_attendance_time = VALUES(last_attendance_time)""",
                                        (id, selected_subject, current_time),
                                    )
                                    connection.commit()
                                    print("Attendance marked successfully!")
                                    attendanceMarked = True
                                    alreadyMarked = False
                                # Get attendance count
                                cursor.execute(
                                    """SELECT attendance_count FROM subject_attendance WHERE student_id = %s AND subject = %s""",
                                    (id, selected_subject),
                                )
                                subject_count = cursor.fetchone()
                                attendance_count = (
                                    subject_count["attendance_count"]
                                    if subject_count
                                    else 0
                                )

                                # Load student image
                                student_img_path = studentInfo.get("image_path", "")
                                if student_img_path and os.path.exists(
                                    student_img_path
                                ):
                                    imgStudent = cv2.imread(student_img_path)
                                    if imgStudent is not None:
                                        imgStudent = cv2.resize(imgStudent, (216, 216))
                                    else:
                                        imgStudent = np.zeros(
                                            (216, 216, 3), dtype=np.uint8
                                        )
                                        imgStudent[:] = (200, 200, 200)
                                else:
                                    imgStudent = np.zeros((216, 216, 3), dtype=np.uint8)
                                    imgStudent[:] = (200, 200, 200)
                                modeType = 1
                                showProfileStartTime = time.time()

                            elif studentInfo is None:
                                print(f"Student not found for ID: {id}")
                                continue
            # Display profile info
            if modeType == 1 and studentInfo:
                # Draw student info
                cv2.putText(
                    imgBackground,
                    str(attendance_count),
                    (861, 125),
                    cv2.FONT_HERSHEY_COMPLEX,
                    1,
                    (255, 255, 255),
                    1,
                )
                cv2.putText(
                    imgBackground,
                    str(studentInfo.get("major", "Unknown")),
                    (1006, 550),
                    cv2.FONT_HERSHEY_COMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )
                cv2.putText(
                    imgBackground,
                    str(id),
                    (1006, 493),
                    cv2.FONT_HERSHEY_COMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )
                # cv2.putText(imgBackground, str(studentInfo.get('standing', 'Unknown')), (910, 625), cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                cv2.putText(
                    imgBackground,
                    str(studentInfo.get("year", "Unknown")),
                    (1025, 625),
                    cv2.FONT_HERSHEY_COMPLEX,
                    0.6,
                    (100, 100, 100),
                    1,
                )
                cv2.putText(
                    imgBackground,
                    str(studentInfo.get("starting_year", "Unknown")),
                    (1125, 625),
                    cv2.FONT_HERSHEY_COMPLEX,
                    0.6,
                    (100, 100, 100),
                    1,
                )

                name = studentInfo.get("name", "Unknown")
                (w, h), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                offset = (414 - w) // 2
                cv2.putText(
                    imgBackground,
                    name,
                    (808 + offset, 445),
                    cv2.FONT_HERSHEY_COMPLEX,
                    1,
                    (50, 50, 50),
                    1,
                )

                if imgStudent is not None:
                    imgBackground[175 : 175 + 216, 909 : 909 + 216] = imgStudent

                if alreadyMarked:
                    cv2.putText(
                        imgBackground,
                        "Attendance Already Marked",
                        (820, 72),
                        cv2.FONT_HERSHEY_COMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )
                elif attendanceMarked:
                    cv2.putText(
                        imgBackground,
                        "Attendance Marked",
                        (820, 72),
                        cv2.FONT_HERSHEY_COMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )

                # Check display duration
                if (time.time() - showProfileStartTime) > displayDuration:
                    modeType = 0
                    id = -1
                    studentInfo = None
                    imgStudent = None
                    attendanceMarked = False
                    alreadyMarked = False
                    showProfileStartTime = 0
            else:
                # Handle unknown face
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)
                cv2.putText(
                    imgBackground,
                    "UNKNOWN STUDENT",
                    (bbox[0], bbox[1] - 10),
                    cv2.FONT_HERSHEY_COMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )
                cv2.putText(
                    imgBackground,
                    "No matching student data",
                    (820, 150),
                    cv2.FONT_HERSHEY_COMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )
                print("Unknown face detected")

            cv2.imshow("Face Attendance", imgBackground)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("Exiting attendance system...")
                break

    except Exception as e:
        print(f"Error in attendance system: {e}")
    finally:
        if "connection" in locals() and connection.is_connected():
            cursor.close()
            connection.close()
        cap.release()
        cv2.destroyAllWindows()


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector

# Your Gmail login credentials
sender_email = "srushtiubale21@gmail.com"  # Replace with your Gmail address
app_password = "mhxp jaxr gabv jxkl"  # Use the generated App Password here

# Database connection details
db_connection = mysql.connector.connect(
    host="localhost",
    user="root",  # Replace with your MySQL username
    password="Ssu@2005",  # Replace with your MySQL password
    database="python_project",  # Replace with your database name
)
# Function to fetch student attendance data
def fetch_attendance_data():
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT s.name, s.student_id, sa.subject, sa.attendance_count, s.email
        FROM students s
        JOIN subject_attendance sa ON s.student_id = sa.student_id
    """
    )
    attendance_data = cursor.fetchall()
    cursor.close()
    return attendance_data


# Function to send email
def send_email(receiver_email, subject, body):
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Attach body to email
    message.attach(MIMEText(body, "plain"))
    try:
        # Set up the server and log in
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)  # Use app password here
            server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"Email sent to {receiver_email} successfully!")
    except Exception as e:
        print(f"Failed to send email to {receiver_email}: {e}")


# Generate email body content
def generate_attendance_email(student):
    name = student["name"]
    subject = student["subject"]
    attendance_count = student["attendance_count"]
    return f"""
    Hello {name},

    Here is your attendance summary for the subject {subject}:
    
    Total Attendance Count: {attendance_count}

    Please keep track of your attendance and make sure to attend future classes.

    Best regards,
    CCOEW
    """


# Fetch attendance data from the database
attendance_data = fetch_attendance_data()
# Set your threshold value for attendance
ATTENDANCE_THRESHOLD = (
    2  # Only send email if attendance count is less than this threshold
)
# Loop through each student and send an attendance email based on the threshold condition
for student in attendance_data:
    # Check if attendance count is below the threshold
    if student["attendance_count"] < ATTENDANCE_THRESHOLD:
        email_body = generate_attendance_email(student)
        student_email = student["email"]  # Fetch the student's actual email
        send_email(student_email, "Your Attendance Summary", email_body)
        print(
            f"Email sent to {student['name']} ({student_email}) due to low attendance."
        )
    else:
        print(
            f"Skipping {student['name']} ({student['email']}) due to sufficient attendance."
        )

# Close database connection
db_connection.close()
# ================== GUI SETUP ==================
root = tk.Tk()
root.title("Student Registration and Attendance")
root.attributes("-fullscreen", True)  # Set the window to full screen
root.configure(bg="#2C3E50")

# Subject Selection Frame
subject_selection_frame = tk.Frame(root, bg="#2C3E50")
title_label = tk.Label(
    subject_selection_frame,
    text="Attendance System",
    font=("Helvetica", 18, "bold"),
    fg="white",
    bg="#2C3E50",
)
title_label.pack(pady=20)

subject_var = tk.StringVar()
subject_combo = ttk.Combobox(
    subject_selection_frame,
    textvariable=subject_var,
    font=("Arial", 14),
    width=30,
    state="readonly",
)
subject_combo["values"] = ("Math", "Physics", "Computer Science", "Robotics")
subject_combo.set("Select a Subject")
subject_combo.pack(pady=20)

# Bind subject selection to the on_subject_selected function
subject_combo.bind("<<ComboboxSelected>>", on_subject_selected)

start_button = tk.Button(
    subject_selection_frame,
    text="Start Attendance",
    command=run_attendance_system,
    font=("Helvetica", 14),
    fg="white",
    bg="#34495E",
    width=20,
    height=2,
)
start_button.pack(pady=30)

register_button = tk.Button(
    subject_selection_frame,
    text="New Registration",
    command=lambda: [subject_selection_frame.pack_forget(), registration_frame.pack()],
    font=("Helvetica", 14),
    fg="white",
    bg="#34495E",
    width=20,
    height=2,
)
register_button.pack(pady=10)

footer_label = tk.Label(
    subject_selection_frame,
    text="Attendance System",
    font=("Arial", 10),
    fg="#BDC3C7",
    bg="#2C3E50",
)
footer_label.pack(side="bottom", pady=10)

# Registration Frame
registration_frame = tk.Frame(root, bg="#2C3E50")
name_var = tk.StringVar()
major_var = tk.StringVar()
starting_year_var = tk.StringVar()
# standing_var = tk.StringVar()
year_var = tk.StringVar()
email_var = tk.StringVar()

# Registration form widgets
tk.Label(
    registration_frame, text="Name", font=("Arial", 14), fg="white", bg="#2C3E50"
).pack(pady=10)
tk.Entry(registration_frame, textvariable=name_var, font=("Arial", 14), width=20).pack(
    pady=10
)

tk.Label(
    registration_frame, text="Major", font=("Arial", 14), fg="white", bg="#2C3E50"
).pack(pady=10)
tk.Entry(registration_frame, textvariable=major_var, font=("Arial", 14), width=20).pack(
    pady=10
)

tk.Label(
    registration_frame,
    text="Starting Year",
    font=("Arial", 14),
    fg="white",
    bg="#2C3E50",
).pack(pady=10)
tk.Entry(
    registration_frame, textvariable=starting_year_var, font=("Arial", 14), width=20
).pack(pady=10)

tk.Label(
    registration_frame, text="Year", font=("Arial", 14), fg="white", bg="#2C3E50"
).pack(pady=10)
tk.Entry(registration_frame, textvariable=year_var, font=("Arial", 14), width=20).pack(
    pady=10
)

tk.Label(
    registration_frame, text="email", font=("Arial", 14), fg="white", bg="#2C3E50"
).pack(pady=10)
tk.Entry(registration_frame, textvariable=email_var, font=("Arial", 14), width=20).pack(
    pady=10
)

upload_button = tk.Button(
    registration_frame,
    text="Upload Image",
    command=upload_image,
    font=("Arial", 14),
    fg="white",
    bg="#34495E",
    width=20,
)
upload_button.pack(pady=10)

image_label = tk.Label(registration_frame, bg="#2C3E50")
image_label.pack(pady=10)

register_student_button = tk.Button(
    registration_frame,
    text="Register Student",
    command=register_student,
    font=("Helvetica", 14),
    fg="white",
    bg="#34495E",
    width=20,
    height=1,
)
register_student_button.pack(pady=20)

back_button = tk.Button(
    registration_frame,
    text="Back",
    command=lambda: [registration_frame.pack_forget(), subject_selection_frame.pack()],
    font=("Helvetica", 14),
    fg="white",
    bg="#34495E",
    width=20,
    height=1,
)
back_button.pack(pady=10)

footer_label = tk.Label(
    registration_frame,
    text="Attendance System",
    font=("Arial", 10),
    fg="#BDC3C7",
    bg="#2C3E50",
)
footer_label.pack(side="bottom", pady=10)

exit_button = tk.Button(
    root,
    text="Exit",
    command=root.quit,
    font=("Helvetica", 14),
    fg="white",
    bg="#E74C3C",
    width=20,
    height=1,
)
exit_button.pack(side="bottom", pady=20)
# Start with subject selection
subject_selection_frame.pack()
# Run the application
root.mainloop()

