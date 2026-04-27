import pathlib


def test_dockerfile_uses_single_worker_for_in_memory_simulation():
    dockerfile = pathlib.Path(__file__).resolve().parents[1] / "Dockerfile"
    text = dockerfile.read_text()

    assert '"--workers", "1"' in text
    assert '"--workers", "2"' not in text


def test_ecs_deploy_uses_single_task_for_in_memory_simulation():
    deploy_workflow = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "deploy.yml"
    text = deploy_workflow.read_text()

    assert "--desired-count 1" in text


def test_ci_python_version_matches_docker_base_image():
    root = pathlib.Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text()
    ci_workflow = (root / ".github" / "workflows" / "ci.yml").read_text()

    assert "FROM python:3.10-slim" in dockerfile
    assert 'python-version: "3.10"' in ci_workflow
