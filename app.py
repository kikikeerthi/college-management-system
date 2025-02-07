from flask import Flask,render_template,request,session,redirect,url_for,flash,current_app, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import login_user,logout_user,login_manager,LoginManager
from flask_login import login_required,current_user
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text


app = Flask(__name__)
app.secret_key='Amanzm00'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:12345678@localhost/college'
db=SQLAlchemy(app)

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Login manager loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User model
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    sid = db.Column(db.String(10), nullable=False,unique=True)
    password = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(10), nullable=False)

# Define models
class Classroom(db.Model):
    __tablename__ = 'classroom'
    building = db.Column(db.String(15), primary_key=True)
    room_number = db.Column(db.String(7), primary_key=True)
    capacity = db.Column(db.Integer)

class Department(db.Model):
    __tablename__ = 'department'
    dept_name = db.Column(db.String(20), primary_key=True)
    building = db.Column(db.String(15))
    budget = db.Column(db.Numeric(12,2))

class Course(db.Model):
    __tablename__ = 'course'
    course_id = db.Column(db.String(8), primary_key=True)
    title = db.Column(db.String(50))
    dept_name = db.Column(db.String(20), db.ForeignKey('department.dept_name'))
    credits = db.Column(db.Integer)
    department = db.relationship('Department', backref=db.backref('courses', lazy=True))

class Instructor(db.Model):
    __tablename__ = 'instructor'
    ID = db.Column(db.String(5), primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    dept_name = db.Column(db.String(20), db.ForeignKey('department.dept_name'))
    salary = db.Column(db.Numeric(8,2))
    department = db.relationship('Department', backref=db.backref('instructors', lazy=True))

class Section(db.Model):
    __tablename__ = 'section'
    course_id = db.Column(db.String(8), db.ForeignKey('course.course_id'), primary_key=True)
    sec_id = db.Column(db.String(8), primary_key=True)
    semester = db.Column(db.String(6), primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    building = db.Column(db.String(15))
    room_number = db.Column(db.String(7))
    time_slot_id = db.Column(db.String(4))
    course = db.relationship('Course', backref=db.backref('sections', lazy=True))
    classroom = db.relationship('Classroom', foreign_keys=[building, room_number], 
                                primaryjoin="and_(Section.building==Classroom.building, Section.room_number==Classroom.room_number)")

class Teaches(db.Model):
    __tablename__ = 'teaches'
    ID = db.Column(db.String(5), db.ForeignKey('instructor.ID'), primary_key=True)
    course_id = db.Column(db.String(8), primary_key=True)
    sec_id = db.Column(db.String(8), primary_key=True)
    semester = db.Column(db.String(6), primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    instructor = db.relationship('Instructor', backref=db.backref('teaches', lazy=True))
    section = db.relationship('Section', foreign_keys=[course_id, sec_id, semester, year], 
                              primaryjoin="and_(Teaches.course_id==Section.course_id, Teaches.sec_id==Section.sec_id, Teaches.semester==Section.semester, Teaches.year==Section.year)")

class Student(db.Model):
    __tablename__ = 'student'
    ID = db.Column(db.String(5), primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    dept_name = db.Column(db.String(20), db.ForeignKey('department.dept_name'))
    tot_cred = db.Column(db.Integer)
    department = db.relationship('Department', backref=db.backref('students', lazy=True))

class Takes(db.Model):
    __tablename__ = 'takes'
    ID = db.Column(db.String(5), db.ForeignKey('student.ID'), primary_key=True)
    course_id = db.Column(db.String(8), primary_key=True)
    sec_id = db.Column(db.String(8), primary_key=True)
    semester = db.Column(db.String(6), primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    grade = db.Column(db.String(2))
    student = db.relationship('Student', backref=db.backref('takes', lazy=True))
    section = db.relationship('Section', foreign_keys=[course_id, sec_id, semester, year], 
                              primaryjoin="and_(Takes.course_id==Section.course_id, Takes.sec_id==Section.sec_id, Takes.semester==Section.semester, Takes.year==Section.year)")

class Advisor(db.Model):
    __tablename__ = 'advisor'
    s_ID = db.Column(db.String(5), db.ForeignKey('student.ID'), primary_key=True)
    i_ID = db.Column(db.String(5), db.ForeignKey('instructor.ID'))
    student = db.relationship('Student', backref=db.backref('advisor', uselist=False))
    instructor = db.relationship('Instructor', backref=db.backref('advisees', lazy=True))

class Prereq(db.Model):
    __tablename__ = 'prereq'
    course_id = db.Column(db.String(8), db.ForeignKey('course.course_id'), primary_key=True)
    prereq_id = db.Column(db.String(8), db.ForeignKey('course.course_id'), primary_key=True)
    course = db.relationship('Course', foreign_keys=[course_id], 
                             primaryjoin="Prereq.course_id==Course.course_id", 
                             backref=db.backref('prereqs', lazy=True))
    prereq_course = db.relationship('Course', foreign_keys=[prereq_id], 
                                    primaryjoin="Prereq.prereq_id==Course.course_id", 
                                    backref=db.backref('required_by', lazy=True))

class Timeslot(db.Model):
    __tablename__ = 'timeslot'
    time_slot_id = db.Column(db.String(4), primary_key=True)
    day = db.Column(db.String(1), primary_key=True)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)

@app.route('/add_sample_user')
def add_sample_user():
    try:
        # Create a sample user and student
        sample_user = User(sid="S1", password="securepassword", role="student")
        
        # Add the user to the User table
        db.session.add(sample_user)
        
        # Create a corresponding student record
        sample_student = Student(ID="S1", name="John Doe", dept_name="Computer Science", tot_cred=0)
        
        # Add the student to the Student table
        db.session.add(sample_student)

        # Create a sample admin user
        sample_admin_user = User(sid="A1", password="adminpassword", role="admin")
        
        # Add the admin user to the User table
        db.session.add(sample_admin_user)

        # Create a sample instructor user
        sample_instructor_user = User(sid="I1", password="instructorpassword", role="instructor")
        
        # Add the instructor user to the User table
        db.session.add(sample_instructor_user)

        # Ensure the department exists in the Department table (assuming "Computer Science")
        department = Department.query.filter_by(dept_name="Computer Science").first()
        if not department:
            department = Department(dept_name="Computer Science")
            db.session.add(department)
            db.session.commit()  # Commit to save the new department

        # Create a corresponding instructor record
        sample_instructor = Instructor(
            ID="I1",
            name="Dr. Alice Smith",
            dept_name="Computer Science",  # Assuming the department is already available
            salary=85000.00,  # Sample salary
            department=department  # Associate with the department
        )
        
        # Add the instructor to the Instructor table
        db.session.add(sample_instructor)

        # Commit the session to save all records
        db.session.commit()
        
        return jsonify({"message": "Sample user, student, and instructor added successfully!"}), 201
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        return jsonify({"error": str(e)}), 400

@app.route('/delete_sample_user')
def delete_sample_user():
    try:
        # Delete the sample user from the User table
        sample_user = User.query.filter_by(sid="S1").first()
        if sample_user:
            db.session.delete(sample_user)

        # Delete the sample admin user from the User table
        sample_admin_user = User.query.filter_by(sid="A1").first()
        if sample_admin_user:
            db.session.delete(sample_admin_user)

        # Delete the sample instructor user from the User table
        sample_instructor_user = User.query.filter_by(sid="I1").first()
        if sample_instructor_user:
            db.session.delete(sample_instructor_user)

        # Delete the student record from the Student table
        sample_student = Student.query.filter_by(ID="S1").first()
        if sample_student:
            db.session.delete(sample_student)

        # Delete the instructor record from the Instructor table
        sample_instructor = Instructor.query.filter_by(ID="I1").first()
        if sample_instructor:
            db.session.delete(sample_instructor)

        # Check if the "Computer Science" department has no other instructors or students
        department = Department.query.filter_by(dept_name="Computer Science").first()
        if department:
            # If no other instructors or students are linked to this department, we can delete it
            if not department.instructors and not department.students:
                db.session.delete(department)

        # Commit the session to delete all the records
        db.session.commit()
        
        return jsonify({"message": "Sample user, student, instructor, and department deleted successfully!"}), 200
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        return jsonify({"error": str(e)}), 400


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        sid = request.form['sid']
        password = request.form['password']
        role = request.form['role']  # Get role from form
        
        user = User.query.filter_by(sid=sid).first()

        if user and user.password== password and user.role == role:
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username, password, or role', 'danger')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return render_template('admin.html')

    elif current_user.role == 'student':
        student = Student.query.filter_by(ID=current_user.sid).first()
        if student:
            courses_taken = Takes.query.filter_by(ID=current_user.sid).all()
            available_courses = Course.query.all()  # Fetch all available courses
            return render_template("student.html", student=student, courses_taken=courses_taken, available_courses=available_courses)
        else:
            return "Student not found", 404

    elif current_user.role == 'instructor':
        instructor = Instructor.query.filter_by(ID=current_user.sid).first()
        if instructor:
            # Get the courses the instructor is currently teaching and join with Course to get course name
            courses_taught = db.session.query(Teaches, Course).join(Course, Teaches.course_id == Course.course_id).filter(Teaches.ID == current_user.sid).all()

            # Get all available courses (those not currently taught by the instructor)
            taught_course_ids = [course.course_id for teach, course in courses_taught]
            available_courses = Course.query.filter(Course.course_id.notin_(taught_course_ids)).all()

            # Get all students (for assigning grades)
            students = Student.query.all()

            # Render the template with instructor info, taught courses, available courses, and students
            return render_template(
                "instructor.html",
                instructor=instructor,
                courses_taught=courses_taught,
                available_courses=available_courses,
                students=students
            )
        else:
            return "Instructor not found", 404

    else:
        return "Invalid role", 403

@app.route('/enroll', methods=['POST'])
@login_required
def enroll():
    course_id = request.form['course_id']
    student_id = current_user.sid

    # Check if the student is already enrolled in the course
    existing_enrollment = Takes.query.filter_by(ID=student_id, course_id=course_id).first()
    if existing_enrollment:
        flash("You are already enrolled in this course.", "warning")
        return redirect(url_for('dashboard'))
    
    # Get the course and section to enroll in
    course = Course.query.filter_by(course_id=course_id).first()
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for('dashboard'))

    # Enroll the student in the course (assuming sec_id is provided or defaulted)
    new_enrollment = Takes(ID=student_id, course_id=course_id, sec_id="A1", semester="Spring", year=2024)
    db.session.add(new_enrollment)
    db.session.commit()
    
    flash("Successfully enrolled in the course!", "success")
    return redirect(url_for('dashboard'))

@app.route('/add_teaches', methods=['POST'])
@login_required
def add_teaches():
    if current_user.role == 'instructor':
        instructor = Instructor.query.filter_by(ID=current_user.sid).first()
        course_id = request.form['course_id']
        
        # Retrieve the selected course from the Course table
        course = Course.query.filter_by(course_id=course_id).first()

        # Retrieve section, semester, and year from form or set defaults
        sec_id = request.form.get('sec_id')  # Assuming section ID is provided by the form
        semester = request.form.get('semester')  # Assuming semester is provided by the form
        year = request.form.get('year')  # Assuming year is provided by the form
        
        # Make sure all required fields are provided
        if instructor and course and sec_id and semester and year:
            # Check if this course is already assigned to the instructor
            existing_teach = Teaches.query.filter_by(
                ID=instructor.ID,
                course_id=course.course_id,
                sec_id=sec_id,
                semester=semester,
                year=year
            ).first()

            if not existing_teach:  # If no record exists
                new_teaches = Teaches(
                    ID=instructor.ID,
                    course_id=course.course_id,
                    sec_id=sec_id,
                    semester=semester,
                    year=year
                )
                db.session.add(new_teaches)
                db.session.commit()

                flash(f"Successfully added {course.title} (Course ID: {course.course_id}) to your teaching schedule for {semester} {year}.", "success")
            else:
                flash(f"You are already assigned to teach {course.title} (Course ID: {course.course_id}) in {semester} {year}.", "warning")
        else:
            flash("Missing required data: course, section, semester, or year.", "danger")

        return redirect(url_for('dashboard'))

    return redirect(url_for('login'))

@app.route('/remmove_teaches/<course_id>', methods=['POST'])
@login_required
def remove_teaches(course_id):
    if current_user.role == 'instructor':
        instructor = Instructor.query.filter_by(ID=current_user.sid).first()
        teaches = Teaches.query.filter_by(ID=instructor.ID, course_id=course_id).first()

        if teaches:
            db.session.delete(teaches)
            db.session.commit()

            flash(f"Successfully removed {teaches.course_id} from your courses.", "success")
        else:
            flash("Course not found in your teaching list.", "danger")

        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/assign_grade', methods=['POST'])
def assign_grade():
    if current_user.role != 'instructor':
        return "Access denied", 403

    course_id = request.form['course_id']
    student_id = request.form['student_id']
    grade = request.form['grade']

    # Verify the instructor teaches the course
    teaches = Teaches.query.filter_by(ID=current_user.sid, course_id=course_id).first()
    if not teaches:
        return "You are not authorized to assign grades for this course", 403

    # Check if the student is enrolled in the course
    takes = Takes.query.filter_by(ID=student_id, course_id=course_id).first()
    if not takes:
        return "The student is not enrolled in this course", 400

    # Assign or update the grade
    takes.grade = grade
    db.session.commit()

    flash("Grade successfully assigned/updated", "success")
    return redirect(url_for('dashboard'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')

    return redirect(url_for('index'))





@app.route('/aboutus')
def  aboutus():
    return render_template("aboutus.html")  



@app.route('/academics')
def  academics():
    return render_template("departments.html")  



@app.route('/admin')
@login_required
def  admin():
    return render_template("admin.html")


@app.route('/student')
@login_required
def student():
    student = Student.query.filter_by(ID=current_user.sid).first()
    if student:
        courses_taken = Takes.query.filter_by(ID=current_user.sid).all()
        return render_template("student.html", student=student, courses_taken=courses_taken)
    else:
        return "Student not found", 404
    
"""__________________________Admin section_______________________________________________"""

@app.route('/sections')
@login_required
def  sections():
    sections = Section.query.order_by(Section.sec_id).all()
    sec = db.session.query(Section.sec_id).distinct().order_by(Section.sec_id).all()
    sec = [s[0] for s in sec]  
    return render_template("sections.html", sections=sections, sec=sec)


@app.route('/add_section', methods=['GET', 'POST'])
@login_required
def add_section():

    course = Course.query.distinct(Course.course_id).all()
    building = db.session.query(Classroom.building).distinct().all()
    room = db.session.query(Classroom.room_number).distinct().all()

    if request.method == "POST":
        id=request.form['id']
        course = request.form['course']
        sem = request.form['sem']
        year = request.form['year']
        building = request.form['building']
        room = request.form['room']
        time = request.form['time']

        try:
            new_sec = Section(course_id=course,sec_id=id,semester=sem,year=year,building=building,room_number=room,time_slot_id=time)
            db.session.add(new_sec)
            db.session.commit()
            flash("Section Added Successfully!", "success")
            return redirect('/sections')
        except SQLAlchemyError as e:
            db.session.rollback()  
            flash("Error occurred while Adding", "danger")
            

    return render_template('add_section.html', course=course,building=building,room=room)




"""____________________________________________________"""

@app.route('/add_course', methods=['GET', 'POST'])
@login_required
def add_course():
    departments = Department.query.distinct(Department.dept_name).all()  # Fetch departments

    if request.method == 'POST':
        id = request.form['id']
        name = request.form['name']
        dept = request.form['dept']
        credits = request.form['credits']

        try:
            # Ensure the course ID is unique
            existing_course = Course.query.filter_by(course_id=id).first()
            if existing_course:
                flash("Course ID already exists. Please choose a different one.", "danger")
                return redirect(url_for('add_course'))

            # Create and add the new course to the database
            new_course = Course(course_id=id, title=name, dept_name=dept, credits=credits)
            db.session.add(new_course)
            db.session.commit()
            flash("Course Added Successfully!", "success")
            return redirect(url_for('departments'))

        except Exception as e:
            db.session.rollback()
            flash("Error occurred while adding course: " + str(e), "danger")
            return redirect(url_for('add_course'))  # Redirect back to the add course page with dept_name parameter

    return render_template('add_course.html', departments=departments)

@app.route('/departments')
@login_required
def  departments():
    return render_template("departments.html")

@app.route('/classrooms')
@login_required
def  classrooms():
    classrooms=Classroom.query.all()

    return render_template("classrooms.html",classrooms=classrooms)




"""____________Instructor_______________________"""
@app.route('/instructors')
@login_required
def  instructors():
    instructors=Instructor.query.all()
    return render_template('instructors.html', instructors = instructors)


@app.route('/update_instructor/<string:ID>', methods=['GET', 'POST'])
@login_required
def update_instructor(ID):
    instructor = Instructor.query.get(ID)
    dept = Department.query.distinct(Department.dept_name).all()

    if request.method == "POST":
        instructor.name = request.form['name']
        instructor.dept_name = request.form['dept']
        instructor.salary = request.form['salary']
        try:
            db.session.commit()
            flash("Profile Updated Successfully!", "success")
            return redirect('/instructors')
        except SQLAlchemyError as e:
            db.session.rollback()  # Rollback the transaction in case of an error
            flash("Error occurred while Updating", "danger")

    return render_template('update_instructor.html', instructor=instructor, departments=dept)



@app.route('/add_instructor', methods=['GET', 'POST'])
@login_required
def add_instructor():

    dept = Department.query.distinct(Department.dept_name).all()

    if request.method == "POST":
        id=request.form['id']
        name = request.form['name']
        dept_name = request.form['dept']
        salary = request.form['salary']

        try:
            existing_course = Instructor.query.filter_by(ID=id).first()
            if existing_course:
                flash("Instructor ID already exists. Please choose a different one.", "danger")
                return redirect(url_for('add_instructor'))
            
            new_instructor = Instructor(ID=id, name=name, dept_name=dept_name, salary=salary)
            db.session.add(new_instructor)
            db.session.commit()
            flash("Instructor Added Successfully!", "success")
            return redirect('/instructors')
        except SQLAlchemyError as e:
            db.session.rollback()  
            flash("Error occurred while Adding", "danger")
            

    return render_template('add_instructor.html', departments=dept)


@app.route('/delete_instructor/<string:ID>', methods=['GET', 'POST'])
@login_required
def delete_instructor(ID):
    instructor = Instructor.query.get(ID)

    if instructor:
        db.session.delete(instructor)
        db.session.commit()
        flash("Instructor Deleted !", "warning")
        return redirect('/instructors')

    return redirect('/instructor')


"""______________________________Studentss___________________________"""
@app.route('/students')
@login_required
def  students():
    student=Student.query.all()
    return render_template("students.html", student = student)


@app.route('/update_student/<string:ID>', methods=['GET', 'POST'])
@login_required
def update_student(ID):
    student=Student.query.get(ID)
    dept = Department.query.distinct(Department.dept_name).all()

    if request.method == "POST":
        student.name = request.form['name']
        student.dept_name = request.form['dept']
        student.tot_cred = request.form['cred']
        try:
            db.session.commit()
            flash("Profile Updated Successfully!", "success")
            return redirect('/students')
        except SQLAlchemyError as e:
            db.session.rollback()  
            flash("Error occurred while Updating", "danger")

    return render_template('update_student.html',student=student, departments=dept)


@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():

    dept = Department.query.distinct(Department.dept_name).all()

    if request.method == "POST":
        id = request.form['id']
        name = request.form['name']
        dept_name = request.form['dept']

        try:
            existing_course = Student.query.filter_by(ID=id).first()
            if existing_course:
                flash("Student ID already exists. Please choose a different one.", "danger")
                return redirect(url_for('add_student'))
            
            new_student = Student(ID=id, name=name, dept_name=dept_name, tot_cred=0)
            new_user=User(sid=id,password=id,role="student")
            db.session.add(new_student)
            db.session.add(new_user)
            db.session.commit()
            flash("Student Added Successfully!", "success")
            return redirect('/students')
        except SQLAlchemyError as e:
            db.session.rollback()  
            flash("Error occurred while Adding", "danger")
            

    return render_template('add_student.html', departments=dept)


@app.route('/delete_student/<string:ID>', methods=['GET', 'POST'])
@login_required
def delete_student(ID):
    student = Student.query.get(ID)
    user = User.query.filter_by(sid=ID).first() 
    if student:
        db.session.delete(student)
        db.session.delete(user)
        db.session.commit()
        flash("Student Removed !", "warning")
        return redirect('/students')

    return redirect('/students')







"""______________________________________________________________________________________________________"""
@app.route('/cse')
def cse():
    query1 = text("""
        SELECT student.ID, student.name
        FROM student
        WHERE student.dept_name = 'Computer Science'
    """)
    query2 = text("""
        SELECT course.course_id, course.title, course.credits
        FROM course
        WHERE course.dept_name = 'Computer Science'
    """)
    query3 = text("""
        SELECT instructor.ID, instructor.name
        FROM instructor
        WHERE instructor.dept_name = 'Computer Science'
    """)
    dept = Department.query.distinct(Department.dept_name).all()

    try:
        # Execute the SQL queries
        students = db.session.execute(query1).fetchall()
        courses = db.session.execute(query2).fetchall()
        instructors = db.session.execute(query3).fetchall()

    except Exception as e:
        students = []  
        courses = []  
        instructors = []
        flash("Error occurred while fetching data", "danger")
   

    return render_template("cse.html", students=students, courses=courses, instructors=instructors,dept=dept)

@app.route('/fin')
def  fin():
    query1 = text("""
        SELECT student.ID, student.name
        FROM student
        WHERE student.dept_name = 'Finance'
    """)
    query2 = text("""
        SELECT course.course_id, course.title, course.credits
        FROM course
        WHERE course.dept_name = 'Finance'
    """)
    query3 = text("""
        SELECT instructor.ID, instructor.name
        FROM instructor
        WHERE instructor.dept_name = 'Finance'
    """)

    try:
        # Execute the SQL queries
        students = db.session.execute(query1).fetchall()
        courses = db.session.execute(query2).fetchall()
        instructors = db.session.execute(query3).fetchall()

    except Exception as e:
        
        flash("Error occurred while fetching data", "danger")
        students = []  
        courses = []  
        instructors = []

    return render_template("fin.html", students=students, courses=courses, instructors=instructors)

@app.route('/hist')
def  hist():

    query1 = text("""
        SELECT student.ID, student.name
        FROM student
        WHERE student.dept_name = 'History'
    """)
    query2 = text("""
        SELECT course.course_id, course.title, course.credits
        FROM course
        WHERE course.dept_name = 'History'
    """)
    query3 = text("""
        SELECT instructor.ID, instructor.name
        FROM instructor
        WHERE instructor.dept_name = 'History'
    """)

    try:
        # Execute the SQL queries
        students = db.session.execute(query1).fetchall()
        courses = db.session.execute(query2).fetchall()
        instructors = db.session.execute(query3).fetchall()

    except Exception as e:
        
        flash("Error occurred while fetching data", "danger")
        students = []  
        courses = []  
        instructors = []
    return render_template("hist.html", students=students, courses=courses, instructors=instructors)


@app.route('/ee')
def  ee():
    query1 = text("""
        SELECT student.ID, student.name
        FROM student
        WHERE student.dept_name = 'Elec. Eng.'
    """)
    query2 = text("""
        SELECT course.course_id, course.title, course.credits
        FROM course
        WHERE course.dept_name = 'Elec. Eng.'
    """)
    query3 = text("""
        SELECT instructor.ID, instructor.name
        FROM instructor
        WHERE instructor.dept_name = 'Elec. Eng.'
    """)

    try:
        students = db.session.execute(query1).fetchall()
        courses = db.session.execute(query2).fetchall()
        instructors = db.session.execute(query3).fetchall()

    except Exception as e:
        flash("Error occurred while fetching data", "danger")
        students = []  
        courses = []  
        instructors = []
    return render_template("ee.html", students=students, courses=courses, instructors=instructors)



@app.route('/bio')
def  bio():
    query1 = text("""
        SELECT student.ID, student.name
        FROM student
        WHERE student.dept_name = 'Biology'
    """)
    query2 = text("""
        SELECT course.course_id, course.title, course.credits
        FROM course
        WHERE course.dept_name = 'Biology'
    """)
    query3 = text("""
        SELECT instructor.ID, instructor.name
        FROM instructor
        WHERE instructor.dept_name = 'Biology'
    """)

    try:
        students = db.session.execute(query1).fetchall()
        courses = db.session.execute(query2).fetchall()
        instructors = db.session.execute(query3).fetchall()

        print(students)
    except Exception as e:
        
        flash("Error occurred while fetching data", "danger")
        students = []  
        courses = []  
        instructors = []
    return render_template("bio.html", students=students, courses=courses, instructors=instructors)


@app.route('/mus')
def  mus():
    query1 = text("""
        SELECT student.ID, student.name
        FROM student
        WHERE student.dept_name = 'Music'
    """)
    query2 = text("""
        SELECT course.course_id, course.title, course.credits
        FROM course
        WHERE course.dept_name = 'Music'
    """)
    query3 = text("""
        SELECT instructor.ID, instructor.name
        FROM instructor
        WHERE instructor.dept_name = 'Music'
    """)

    try:
        students = db.session.execute(query1).fetchall()
        courses = db.session.execute(query2).fetchall()
        instructors = db.session.execute(query3).fetchall()

        print(students)
    except Exception as e:
        
        flash("Error occurred while fetching data", "danger")
        students = []  
        courses = []  
        instructors = [] 
    return render_template("mus.html", students=students, courses=courses, instructors=instructors)


@app.route('/phy')
def  phy():
    query1 = text("""
        SELECT student.ID, student.name
        FROM student
        WHERE student.dept_name = 'Physics'
    """)
    query2 = text("""
        SELECT course.course_id, course.title, course.credits
        FROM course
        WHERE course.dept_name = 'Physics'
    """)
    query3 = text("""
        SELECT instructor.ID, instructor.name
        FROM instructor
        WHERE instructor.dept_name = 'Physics'
    """)

    try:
        students = db.session.execute(query1).fetchall()
        courses = db.session.execute(query2).fetchall()
        instructors = db.session.execute(query3).fetchall()

        print(students)
    except Exception as e:
        
        flash("Error occurred while fetching data", "danger")
        students = []  
        courses = []  
        instructors = []
    return render_template("phy.html", students=students, courses=courses, instructors=instructors)


if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()  # Ensure all tables are created
            print("Database tables created successfully!")
        except SQLAlchemyError as e:
            print(f"Error creating tables: {e}")
    app.run(debug=True)