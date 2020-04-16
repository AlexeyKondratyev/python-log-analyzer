
import unittest
import json
import log_analyzer


class Test_config_parsing(unittest.TestCase):

    sample_path = './test_sample/'

    def test_config_parsing_bad_path(self):
        test_bad_path = "sd234;l,wer#L<d"
        self.assertIsNone(log_analyzer.config_parsing(test_bad_path))

    def test_config_parsing_good_path(self):
        test_good_path = "./app.cfg.example"
        json_data = log_analyzer.config_parsing(test_good_path)
        self.assertIn('REPORT_SIZE', json_data)
        self.assertIn('ERROR_LIMIT_PERC', json_data)
        self.assertIn('REPORT_DIR', json_data)
        self.assertIn('URL_LOG_DIR', json_data)
        self.assertIn('CONFIG_FILE_FULL_PATH', json_data)
        self.assertIn('LOG_FILE_FULL_PATH', json_data)

    def test_report_existence_check_bad_path(self):
        test_path = '/etc/!@#$%^&*()'
        self.assertIsNone(log_analyzer.report_existence_check(test_path))

    def test_log_file_existence_check_from_sample(self):
        self.assertEqual(log_analyzer.log_file_existence_check(self.sample_path),
                         './test_sample/nginx-access-ui.log-20991231.gz')

    def test_log_file_parsing_and_get_top_from_sample(self):
        full_path = log_analyzer.log_file_existence_check(self.sample_path)
        urls, urls_count, urls_total_time, error_perc = log_analyzer.log_file_parsing(full_path)
        report_size = 10
        _top = log_analyzer.get_top_requests(urls, urls_count, urls_total_time, report_size)
        result_list = [i[1] for i in _top.items()]
        self.assertIsNotNone(urls['7e0f54c1ef851fb3'])
        self.assertEqual(urls_count, 100)
        self.assertEqual(urls_total_time, 25.840999999999994)
        self.assertEqual(error_perc, 0.00)
        self.assertEqual(result_list[0]['time_max'], 5.246)


if __name__ == '__main__':
    unittest.main()