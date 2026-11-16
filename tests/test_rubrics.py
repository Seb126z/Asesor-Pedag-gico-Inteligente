from app.services.rubrics import validate_rubric, calculate_grade

def test_valid_rubric():
    result = validate_rubric([{"name": "A", "weight": 40}, {"name": "B", "weight": 60}])
    assert result["valid"] is True

def test_invalid_weight_total():
    result = validate_rubric([{"name": "A", "weight": 40}])
    assert result["valid"] is False

def test_backend_grade_calculation():
    assert calculate_grade([{"score": 4, "weight": 25}, {"score": 5, "weight": 75}]) == 4.75
