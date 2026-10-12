from datetime import date, datetime
from werkzeug.security import generate_password_hash
from app import app, db
from models import *

def seed_database():
    with app.app_context():
        # Check if database is already seeded
        count = db.session.query(func.count(User.id)).scalar()
        if count > 0:
            print("Database already seeded")
            return
            
        print("Seeding database...")
        
        # Create departments
        departments = [
            Department(code="CSE", name="Computer Science & Engineering", short_name="CSE", is_active=True),
            Department(code="AIDS", name="Artificial Intelligence & Data Science", short_name="AI&DS", is_active=True),
            Department(code="ECE", name="Electronics & Communication Engineering", short_name="ECE", is_active=True),
            Department(code="ME", name="Mechanical Engineering", short_name="ME", is_active=True),
            Department(code="CE", name="Civil Engineering", short_name="Civil", is_active=True),
            Department(code="EE", name="Electrical Engineering", short_name="EE", is_active=True),
            Department(code="MBA", name="Master of Business Administration", short_name="MBA", is_active=True),
        ]
        
        # Create categories
        categories = [
            Category(name="Programming", description="Programming languages, software development and engineering"),
            Category(name="Machine Learning", description="Machine learning, AI and data science"),
            Category(name="Computer Networks", description="Networking, protocols and distributed systems"),
            Category(name="Database Systems", description="Database design, SQL and data management"),
            Category(name="Web Development", description="Web platforms and application development"),
            Category(name="Operating Systems", description="Operating systems and computer architecture"),
            Category(name="Mathematics", description="Mathematics, statistics and quantitative methods"),
            Category(name="Management", description="Business, leadership and organizational studies"),
        ]
        
        # Create publishers
        publishers = [
            Publisher(name="Pearson", website="https://www.pearson.com/"),
            Publisher(name="O'Reilly Media", website="https://www.oreilly.com/"),
            Publisher(name="MIT Press", website="https://mitpress.mit.edu/"),
            Publisher(name="Prentice Hall", website="https://www.pearson.com/"),
            Publisher(name="McGraw Hill", website="https://www.mheducation.com/"),
            Publisher(name="Wiley", website="https://www.wiley.com/"),
            Publisher(name="Manning Publications", website="https://www.manning.com/"),
        ]
        
        # Create authors
        authors = [
            Author(name="Robert C. Martin"),
            Author(name="Aurélien Géron"),
            Author(name="Andrew S. Tanenbaum"),
            Author(name="David J. Wetherall"),
            Author(name="Abraham Silberschatz"),
            Author(name="Henry F. Korth"),
            Author(name="Paul Barry"),
            Author(name="Eric Matthes"),
            Author(name="Ian Goodfellow"),
            Author(name="Yoshua Bengio"),
            Author(name="Aaron Courville"),
            Author(name="Thomas H. Cormen"),
            Author(name="Charles E. Leiserson"),
            Author(name="Ronald L. Rivest"),
            Author(name="Clifford Stein"),
            Author(name="Martin Kleppmann"),
        ]
        
        # Add all entities to session (except books)
        for item in departments + categories + publishers + authors:
            db.session.add(item)
        db.session.flush()  # Flush to get IDs
        
        # Create books with proper category IDs
        books = [
            Book(isbn="9780132350884", title="Clean Code", subtitle="A Handbook of Agile Software Craftsmanship", description="Practical principles for writing readable, maintainable software.", publication_year=2008, edition="1st", language="English", publisher_id=publishers[0].id, category_id=categories[0].id),
            Book(isbn="9781491962299", title="Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow", subtitle="Concepts, Tools, and Techniques to Build Intelligent Systems", description="Practical machine learning with Python and modern frameworks.", publication_year=2019, edition="2nd", language="English", publisher_id=publishers[1].id, category_id=categories[1].id),
            Book(isbn="9780135941414", title="Computer Networking: A Top-Down Approach", subtitle="", description="Networking concepts using a top-down Internet approach.", publication_year=2016, edition="7th", language="English", publisher_id=publishers[0].id, category_id=categories[2].id),
            Book(isbn="9780073523323", title="Database System Concepts", subtitle="", description="Core database systems concepts, architecture and design.", publication_year=2019, edition="7th", language="English", publisher_id=publishers[4].id, category_id=categories[3].id),
            Book(isbn="9781593279288", title="Python Crash Course", subtitle="A Hands-On, Project-Based Introduction to Programming", description="Project-based Python programming for beginners.", publication_year=2019, edition="2nd", language="English", publisher_id=publishers[1].id, category_id=categories[0].id),
            Book(isbn="9780262046305", title="Deep Learning", subtitle="", description="Foundational treatment of deep learning theory and practice.", publication_year=2016, edition="1st", language="English", publisher_id=publishers[2].id, category_id=categories[1].id),
        ]
        
        for item in books:
            db.session.add(item)
        db.session.flush()
        
        # Create book_departments relationships using the association table
        book_departments_data = []
        # Assign relevance to books based on category
        for book in books:
            if book.category_id == categories[0].id:  # Programming
                for dept in departments[:3]:  # CSE, AIDS, ECE
                    book_departments_data.append({"book_id": book.id, "department_id": dept.id, "relevance": 5})
            elif book.category_id == categories[1].id:  # Machine Learning
                for dept in departments[:2]:  # CSE, AIDS
                    book_departments_data.append({"book_id": book.id, "department_id": dept.id, "relevance": 5})
            else:
                for dept in departments[3:]:  # ECE, ME, CE, EE, MBA
                    book_departments_data.append({"book_id": book.id, "department_id": dept.id, "relevance": 3})
                    
        # Insert into association table
        for bd in book_departments_data:
            db.session.execute(
                book_departments.insert().values(**bd)
            )
            
        # Create book_authors relationships
        book_authors_data = [
            {"book_id": books[0].id, "author_id": authors[0].id},  # Clean Code - Robert C. Martin
            {"book_id": books[1].id, "author_id": authors[1].id},  # Hands-On ML - Aurélien Géron
            {"book_id": books[2].id, "author_id": authors[2].id},  # Computer Networking - Tanenbaum
            {"book_id": books[2].id, "author_id": authors[3].id},  # Computer Networking - Wetherall
            {"book_id": books[3].id, "author_id": authors[4].id},  # Database Systems - Silberschatz
            {"book_id": books[3].id, "author_id": authors[5].id},  # Database Systems - Korth
            {"book_id": books[4].id, "author_id": authors[7].id},  # Python Crash Course - Eric Matthes
            {"book_id": books[5].id, "author_id": authors[8].id},  # Deep Learning - Goodfellow
            {"book_id": books[5].id, "author_id": authors[9].id},  # Deep Learning - Bengio
            {"book_id": books[5].id, "author_id": authors[10].id}, # Deep Learning - Courville
        ]
        
        for ba in book_authors_data:
            db.session.execute(
                book_authors.insert().values(**ba)
            )
            
        # Create book_copies (3-5 copies per book) with unique accession numbers and barcodes
        acquired_date = date(2024, 7, 15)
        book_copies = []
        copy_counter = 0
        for i, book in enumerate(books):
            # Generate 3-5 copies per book
            copy_count = 3 if book.category_id == categories[0].id else 5  # More copies for programming books
            for j in range(copy_count):
                copy_counter += 1
                book_copies.append(BookCopy(
                    book_id=book.id,
                    accession_number=f"MITRC-{str(copy_counter).zfill(4)}",
                    barcode=f"LIB-{str(copy_counter).zfill(6)}",
                    rack=f"CS-{chr(65 + (j % 4))}" if book.category_id == categories[0].id else f"AI-{chr(65 + (j % 4))}",
                    shelf=f"S-{((j % 8) + 1)}",
                    status="AVAILABLE",
                    condition="GOOD",
                    acquired_at=acquired_date
                ))
                
        for copy in book_copies:
            db.session.add(copy)
        db.session.flush()
            
        # Create sample users
        password_hash = generate_password_hash("LibSphere@2026")
        users = [
            User(name="Aarav Mehta", email="aarav.mehta@mitrc.ac.in", password_hash=password_hash, role="STUDENT", department_id=departments[0].id),
            User(name="Rohan Gupta", email="rohan.gupta@mitrc.ac.in", password_hash=password_hash, role="STUDENT", department_id=departments[0].id),
            User(name="Sneha Malhotra", email="sneha.malhotra@mitrc.ac.in", password_hash=password_hash, role="STUDENT", department_id=departments[0].id),
            User(name="Dr. Priya Sharma", email="priya.sharma@mitrc.ac.in", password_hash=password_hash, role="DEPARTMENT", department_id=departments[0].id),
        ]
        
        for user in users:
            db.session.add(user)
        db.session.flush()
            
        # Create some sample loans with datetime objects
        issued_dt = datetime(2026, 4, 1, 9, 0, 0)
        due_dt = datetime(2026, 4, 15, 9, 0, 0)
        
        for i, user in enumerate(users[:3]):  # Only students get loans
            book_copy = book_copies[i]  # Use first few copies
            loan = Loan(
                user_id=user.id,
                book_copy_id=book_copy.id,
                issued_at=issued_dt,
                due_at=due_dt,
                returned_at=due_dt,
                status="RETURNED",
                issued_by=user.id,
                returned_to=user.id
            )
            db.session.add(loan)
            
        db.session.commit()
        print("Database seeded successfully")

if __name__ == "__main__":
    seed_database()
