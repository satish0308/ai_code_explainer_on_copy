"""
Tests to verify pyproject.toml is properly configured.
"""

import os

import toml


def test_pyproject_exists():
    """Test that pyproject.toml exists."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    assert os.path.exists(pyproject_path), "pyproject.toml should exist"


def test_pyproject_has_name():
    """Test that pyproject.toml has a name."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    with open(pyproject_path) as f:
        config = toml.load(f)
    assert "tool" in config
    assert "poetry" in config["tool"]
    assert "name" in config["tool"]["poetry"]
    assert config["tool"]["poetry"]["name"] == "auto-code-explainer"


def test_pyproject_has_version():
    """Test that pyproject.toml has a version."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    with open(pyproject_path) as f:
        config = toml.load(f)
    assert "tool" in config
    assert "poetry" in config["tool"]
    assert "version" in config["tool"]["poetry"]


def test_pyproject_has_description():
    """Test that pyproject.toml has a description."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    with open(pyproject_path) as f:
        config = toml.load(f)
    assert "description" in config["tool"]["poetry"]


def test_pyproject_has_author():
    """Test that pyproject.toml has an author."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    with open(pyproject_path) as f:
        config = toml.load(f)
    assert "authors" in config["tool"]["poetry"]
    assert len(config["tool"]["poetry"]["authors"]) > 0


def test_pyproject_has_dependencies():
    """Test that pyproject.toml has dependencies."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    with open(pyproject_path) as f:
        config = toml.load(f)
    assert "dependencies" in config["tool"]["poetry"]
    assert "python" in config["tool"]["poetry"]["dependencies"]


def test_pyproject_has_license():
    """Test that pyproject.toml has a license."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    with open(pyproject_path) as f:
        config = toml.load(f)
    assert "license" in config["tool"]["poetry"]


def test_pyproject_has_readme():
    """Test that pyproject.toml has a README reference."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    with open(pyproject_path) as f:
        config = toml.load(f)
    assert "readme" in config["tool"]["poetry"]
