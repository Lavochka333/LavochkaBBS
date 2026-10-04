import unittest
from unittest.mock import Mock
from types import SimpleNamespace
import numpy as np
from detect import Detect


class GpuFallbackTests(unittest.TestCase):
    def test_unicode_gpu_failure_retries_same_frame_on_cpu(self):
        detector = object.__new__(Detect)
        detector.device = 'DmlExecutionProvider'
        detector.input_name = 'images'
        detector.model = Mock()
        detector.model.run.side_effect = UnicodeDecodeError('utf-8', b'\xcd', 0, 1, 'invalid continuation byte')
        tensor = np.zeros((1,3,640,640), dtype=np.float32)
        detector.preprocess_image = Mock(return_value=(tensor,640,640))
        detector.postprocess = Mock(return_value=[])
        cpu = Mock()
        cpu.get_inputs.return_value = [SimpleNamespace(name='images')]
        detector.load_model = Mock(return_value=(cpu,'CPUExecutionProvider'))
        self.assertEqual(detector.detect_objects(np.zeros((900,1600,3),dtype=np.uint8)), {})
        self.assertEqual(detector.preferred_device, 'cpu')
        self.assertEqual(detector.device, 'CPUExecutionProvider')
        cpu.run.assert_called_once()
        self.assertIs(cpu.run.call_args.args[1]['images'], tensor)

    def test_cpu_error_is_reported_without_infinite_retry(self):
        detector = object.__new__(Detect)
        detector.device = 'CPUExecutionProvider'
        detector.input_name = 'images'
        detector.model = Mock()
        detector.model.run.side_effect = RuntimeError('bad model')
        detector.preprocess_image = Mock(return_value=(np.zeros((1,3,640,640)),640,640))
        with self.assertRaisesRegex(RuntimeError, 'bad model'):
            detector.detect_objects(np.zeros((900,1600,3),dtype=np.uint8))
        detector.model.run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
