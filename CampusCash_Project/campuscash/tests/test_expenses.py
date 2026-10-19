from database import add_expense, update_expense, delete_expense, get_expenses, monthly_total
from auth import register_user

def user(db):
    assert register_user("owner", "campus123", "campus123", db)[0]

def payload(amount=120):
    return {"date":"2026-10-04","category":"Food","amount":amount,"payment_method":"UPI",
            "description":"Lunch","merchant":"Cafe","tags":"meal"}

def test_crud_and_month_total(db_path):
    user(db_path)
    eid=add_expense("owner",payload(),db_path)
    assert monthly_total("owner","2026-10",db_path)==(120.0,1)
    assert update_expense("owner",eid,payload(200),db_path)
    assert monthly_total("owner","2026-10",db_path)==(200.0,1)
    assert not update_expense("other",eid,payload(300),db_path)
    assert delete_expense("owner",eid,db_path)
    assert monthly_total("owner","2026-10",db_path)==(0.0,0)

def test_user_isolation_and_filters(db_path):
    user(db_path)
    add_expense("owner",payload(),db_path)
    assert get_expenses("other",db_path).empty
    assert len(get_expenses("owner",db_path,start="2026-10-01",end="2026-10-31",category="Food"))==1
    assert get_expenses("owner",db_path,start="2026-11-01",end="2026-11-30").empty
