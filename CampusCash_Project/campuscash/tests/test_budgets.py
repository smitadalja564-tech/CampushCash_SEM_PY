from database import save_budget, get_budget, add_expense, monthly_total
from auth import register_user
from utils import valid_amount, valid_budget, valid_date

def test_budget_upsert_and_overspend(db_path):
    register_user("budgetuser","campus123","campus123",db_path)
    save_budget("budgetuser","2026-10",1000,db_path)
    save_budget("budgetuser","2026-10",800,db_path)
    assert get_budget("budgetuser","2026-10",db_path)==800
    add_expense("budgetuser",{"date":"2026-10-19","category":"Food","amount":950,
        "payment_method":"Cash","description":"","merchant":"","tags":""},db_path)
    total,_=monthly_total("budgetuser","2026-10",db_path)
    assert total > get_budget("budgetuser","2026-10",db_path)

def test_validators():
    assert valid_amount(1)
    for bad in [0,-1,"NaN","inf","x",None]: assert not valid_amount(bad)
    assert valid_budget(0) and not valid_budget(-1)
    assert valid_date("2026-10-19") and not valid_date("19/10/2026")
