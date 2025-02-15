# ==============================================================================
#  Copyright (c) 2024 Sam Hart                                                 =
#  <contact@justsam.io>                                                        =
#                                                                              =
#  Permission is hereby granted, free of charge, to any person obtaining a     =
#  copy of this software and associated documentation files (the "Software"),  =
#  to deal in the Software without restriction, including without limitation   =
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,    =
#  and/or sell copies of the Software, and to permit persons to whom the       =
#  Software is furnished to do so, subject to the following conditions:        =
#                                                                              =
#  The above copyright notice and this permission notice shall be included in  =
#  all copies or substantial portions of the Software.                         =
#                                                                              =
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR  =
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,    =
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL     =
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER  =
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING     =
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER         =
#  DEALINGS IN THE SOFTWARE.                                                   =
# ==============================================================================
import pytest
from click.testing import CliRunner

from fuseline.cli.__main__ import ls, run
from fuseline.core.config import FuselineConfig


@pytest.fixture
def mock_get_fuseline_config(mocker):
    mock_config = FuselineConfig.model_validate(
        {
            "config": {"engine": "SerialEngine"},
            "workflows": [
                {
                    "name": "test_eval",
                    "outputs": ["fuseline.workflows.fake_eval.evaluate_model"],
                }
            ],
        }
    )

    # Set up mock config here
    mocker.patch("fuseline.core.config.get_fuseline_config", return_value=mock_config)
    return mock_config


def test_ls_command(mock_get_fuseline_config):
    runner = CliRunner()
    result = runner.invoke(ls)
    assert result.exit_code == 0
    # Add more assertions to check the output


def test_run_command_workflow_not_found(mock_get_fuseline_config):
    runner = CliRunner()
    result = runner.invoke(run, ["non_existent_workflow"])
    assert result.exit_code == 0
    assert "ERROR! Workflow `non_existent_workflow` not found." in result.output


def test_run_command_successful(mock_get_fuseline_config):
    # Set up a mock workflow in your mock_get_fuseline_config
    runner = CliRunner()
    result = runner.invoke(run, ["existing_workflow", "--param1", "value1"])
    assert result.exit_code == 0
    # Add more assertions to check the output


def test_run_command_with_exception(mock_get_fuseline_config):
    # Set up a mock workflow that raises an exception
    runner = CliRunner()
    result = runner.invoke(run, ["exception_workflow"])
    assert result.exit_code == 0
    assert "ERROR!" in result.output


def test_ls_command_detailed_output(mock_get_fuseline_config):
    runner = CliRunner()
    result = runner.invoke(ls)
    assert result.exit_code == 0
    assert "Workflow Name" in result.output
    assert "Input Shape" in result.output
    assert "Outputs" in result.output
    assert "fake_eval" in result.output
    assert "Engine: SerialEngine" in result.output


def test_run_command_with_different_parameter_types(mock_get_fuseline_config, mocker):
    runner = CliRunner()
    result = runner.invoke(
        run, ["fake_eval", "--true_positives", "42", "--false_positives", "3", "--false_negatives", "1"]
    )

    assert result.exit_code == 0
    assert "Excellent" in result.output


def test_run_command_with_none_config(mocker):
    mocker.patch("fuseline.cli.__main__.get_fuseline_config", return_value=None)
    runner = CliRunner()
    result = runner.invoke(run, ["test_workflow"])

    assert result.exit_code == 0
    assert "unable to read `pyproject.toml` configuration" in result.output


def test_run_command_with_workflow_not_found_error(mock_get_fuseline_config, mocker):
    runner = CliRunner()
    result = runner.invoke(run, ["test_workflow"])

    assert result.exit_code == 0
    assert "ERROR! Workflow `test_workflow` not found." in result.output
