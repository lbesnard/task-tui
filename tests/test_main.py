"""Tests for main entry point and CLI."""
import pytest
from unittest.mock import Mock, patch
from task_tui.app import run, check_taskwarrior_installed


@pytest.mark.unit
class TestMainEntry:
    """Tests for the run() function and CLI entry point."""
    
    @patch('task_tui.app.check_taskwarrior_installed')
    @patch('task_tui.app.load_app_config')
    @patch('task_tui.app.TaskProApp')
    def test_run_with_default_args(self, mock_app_class, mock_load_config, mock_check_tw):
        """Test run() with default arguments."""
        mock_check_tw.return_value = True
        mock_load_config.return_value = {"shortcuts": {}}
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        
        with patch('sys.argv', ['task-tui']):
            run()
        
        mock_check_tw.assert_called_once()
        mock_load_config.assert_called_once()
        mock_app_class.assert_called_once_with(config={"shortcuts": {}})
        assert mock_app.no_sync is False
        mock_app.run.assert_called_once()
    
    @patch('task_tui.app.check_taskwarrior_installed')
    @patch('task_tui.app.load_app_config')
    @patch('task_tui.app.TaskProApp')
    def test_run_with_no_sync_flag(self, mock_app_class, mock_load_config, mock_check_tw):
        """Test run() with --no-sync flag."""
        mock_check_tw.return_value = True
        mock_load_config.return_value = {"shortcuts": {}}
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        
        with patch('sys.argv', ['task-tui', '--no-sync']):
            run()
        
        assert mock_app.no_sync is True
        mock_app.run.assert_called_once()
    
    def test_run_version_flag(self):
        """Test run() with --version flag exits with code 0."""
        # ArgumentParser's --version action calls sys.exit(0)
        # We just verify the flag is recognized and exits cleanly
        with patch('sys.argv', ['task-tui', '--version']):
            with patch('sys.stdout'):  # Suppress version output
                try:
                    run()
                    assert False, "Should have raised SystemExit"
                except SystemExit as e:
                    assert e.code == 0
    
    @patch('task_tui.app.check_taskwarrior_installed')
    @patch('builtins.print')
    def test_run_taskwarrior_not_installed(self, mock_print, mock_check_tw):
        """Test run() when taskwarrior is not installed."""
        mock_check_tw.return_value = False
        
        with patch('sys.argv', ['task-tui']):
            with pytest.raises(SystemExit) as exc_info:
                run()
            assert exc_info.value.code == 1
        
        mock_check_tw.assert_called_once()
        
        # Check error messages were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any('Error' in str(call) for call in print_calls)
        assert any('Taskwarrior' in str(call) for call in print_calls)
    
    @patch('task_tui.app.check_taskwarrior_installed')
    @patch('task_tui.app.load_app_config')
    @patch('task_tui.app.TaskProApp')
    @patch('builtins.print')
    def test_run_keyboard_interrupt(self, mock_print, mock_app_class, mock_load_config, mock_check_tw):
        """Test run() handles KeyboardInterrupt gracefully."""
        mock_check_tw.return_value = True
        mock_load_config.return_value = {"shortcuts": {}}
        mock_app = Mock()
        mock_app.run.side_effect = KeyboardInterrupt()
        mock_app_class.return_value = mock_app
        
        with patch('sys.argv', ['task-tui']):
            run()
        
        # Check graceful exit message
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any('closed' in str(call).lower() for call in print_calls)
    
    @patch('task_tui.app.check_taskwarrior_installed')
    @patch('task_tui.app.load_app_config')
    @patch('task_tui.app.TaskProApp')
    @patch('builtins.print')
    def test_run_unexpected_exception(self, mock_print, mock_app_class, mock_load_config, mock_check_tw):
        """Test run() handles unexpected exceptions."""
        mock_check_tw.return_value = True
        mock_load_config.return_value = {"shortcuts": {}}
        mock_app = Mock()
        test_error = RuntimeError("Test error")
        mock_app.run.side_effect = test_error
        mock_app_class.return_value = mock_app
        
        with patch('sys.argv', ['task-tui']):
            with pytest.raises(SystemExit) as exc_info:
                run()
            assert exc_info.value.code == 1
        
        # Check error was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any('error' in str(call).lower() for call in print_calls)
        assert any('Test error' in str(call) for call in print_calls)
    
    @patch('task_tui.app.check_taskwarrior_installed')
    @patch('task_tui.app.load_app_config')
    @patch('task_tui.app.TaskProApp')
    def test_run_sets_no_sync_attribute(self, mock_app_class, mock_load_config, mock_check_tw):
        """Test run() properly sets no_sync attribute on app instance."""
        mock_check_tw.return_value = True
        mock_load_config.return_value = {"shortcuts": {}}
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        
        # Test with no_sync=False (default)
        with patch('sys.argv', ['task-tui']):
            run()
        assert mock_app.no_sync is False
        
        # Test with no_sync=True
        with patch('sys.argv', ['task-tui', '--no-sync']):
            run()
        assert mock_app.no_sync is True
    
    @patch('task_tui.app.check_taskwarrior_installed')
    @patch('task_tui.app.load_app_config')
    @patch('task_tui.app.TaskProApp')
    def test_run_app_initialization(self, mock_app_class, mock_load_config, mock_check_tw):
        """Test run() initializes TaskProApp correctly."""
        mock_check_tw.return_value = True
        mock_load_config.return_value = {"shortcuts": {}}
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        
        with patch('sys.argv', ['task-tui']):
            run()
        
        # Verify app was created and run
        mock_app_class.assert_called_once_with(config={"shortcuts": {}})
        mock_app.run.assert_called_once_with()
