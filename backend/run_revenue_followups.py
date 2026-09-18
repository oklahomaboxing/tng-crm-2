from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.revenue.followups import run_due_followups


def main():
    db = SessionLocal()

    try:
        result = run_due_followups(db)
        print("Revenue follow-up job complete:")
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
