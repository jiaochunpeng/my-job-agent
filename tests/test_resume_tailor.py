import pytest
from unittest.mock import patch, MagicMock
from src.resume_tailor import compute_match_score, tailor_resume, load_base_resume

def test_load_base_resume(tmp_path):
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Joseph Jiao\nData Leader")
    content = load_base_resume(str(resume_file))
    assert "Joseph Jiao" in content
    assert "Data Leader" in content

def test_compute_match_score_high_match(sample_jd, sample_resume):
    with patch("src.resume_tailor.get_llm_client") as mock_get:
        mock_client = MagicMock()
        mock_client.query.return_value = "85"
        mock_get.return_value = mock_client
        score = compute_match_score(sample_jd, sample_resume)
        assert score == 85
        mock_client.query.assert_called_once()

def test_compute_match_score_low_match(sample_jd, sample_resume):
    with patch("src.resume_tailor.get_llm_client") as mock_get:
        mock_client = MagicMock()
        mock_client.query.return_value = "35"
        mock_get.return_value = mock_client
        score = compute_match_score(sample_jd, sample_resume)
        assert score == 35

def test_compute_match_score_handles_non_numeric(sample_jd, sample_resume):
    with patch("src.resume_tailor.get_llm_client") as mock_get:
        mock_client = MagicMock()
        mock_client.query.return_value = "around 80%"
        mock_get.return_value = mock_client
        score = compute_match_score(sample_jd, sample_resume)
        assert score == 0

def test_tailor_resume(sample_jd, sample_resume):
    with patch("src.resume_tailor.get_llm_client") as mock_get:
        mock_client = MagicMock()
        mock_client.query.return_value = "# Tailored Resume\nEnhanced version"
        mock_get.return_value = mock_client
        tailored = tailor_resume(sample_jd, sample_resume)
        assert "Tailored Resume" in tailored
        assert "Enhanced" in tailored
