# Copyright 2019, The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import itertools

from absl.testing import parameterized
import numpy as np
import scipy.linalg
import tensorflow as tf

from tensorflow_model_optimization.python.core.internal.tensor_encoding.utils import tf_utils


if tf.executing_eagerly():
  tf.compat.v1.disable_eager_execution()


class FastWalshHadamardTransformTests(tf.test.TestCase, parameterized.TestCase):
  """Tests for `fast_walsh_hadamard_transform` method."""

  @parameterized.parameters([2, 4, 8, 16])
  def test_is_rotation(self, dim):
    """Tests the transform acts as a rotation."""
    x = tf.random.normal([1, dim])
    hx = tf_utils.fast_walsh_hadamard_transform(x)
    x, hx = self.evaluate([x, hx])
    # Check that x and hx are not the same, but have equal norm.
    self.assertGreater(np.linalg.norm(x - hx), 1e-3)
    self.assertAllClose(np.linalg.norm(x), np.linalg.norm(hx))

  @parameterized.parameters([1, 2, 5, 11])
  def test_apply_twice_equals_identity(self, first_dim):
    """Tests applying the transform twice is equal to identity."""
    x = tf.random.normal([first_dim, 8])
    hx = tf_utils.fast_walsh_hadamard_transform(x)
    hhx = tf_utils.fast_walsh_hadamard_transform(hx)
    x, hhx = self.evaluate([x, hhx])
    self.assertAllEqual(x.shape, hhx.shape)
    self.assertAllClose(x, hhx)

  @parameterized.parameters([[1], [1, 4, 4], [1, 1, 1, 4]])
  def test_illegal_inputs_shape(self, *dims):
    """Tests incorrect rank of the input."""
    x = tf.random.normal(dims)
    with self.assertRaisesRegex(
        ValueError, 'Number of dimensions of x must be 2.'
    ):
      tf_utils.fast_walsh_hadamard_transform(x)

  @parameterized.parameters([[1, 3], [1, 7], [1, 9], [4, 3]])
  def test_illegal_inputs_static_power_of_two(self, *dims):
    """Tests incorrect static shape of the rank 2 input."""
    x = tf.random.normal(dims)
    with self.assertRaisesRegex(
        ValueError, 'The dimension of x must be a power of two.'
    ):
      tf_utils.fast_walsh_hadamard_transform(x)

  def test_illegal_inputs_dynamic_power_of_two(self):
    """Tests incorrect dynamic shape of the rank 2 input."""
    rand = tf.random.uniform((), maxval=3, dtype=tf.int32) + 1
    # The created x has shape (3, 3) or (3, 9) or (3, 27), chosen randomly and
    # thus statically not known. In all cases, it is not a power of two.
    x = tf.random.normal((3, 3**rand))
    hx = tf_utils.fast_walsh_hadamard_transform(x)
    with self.assertRaisesOpError('The dimension of x must be a power of two.'):
      hx = self.evaluate(hx)

  @parameterized.parameters([[1, 1], [4, 1], [2, 2], [1, 8], [1, 4]])
  def test_static_input_shape(self, *dims):
    """Tests static input shape."""
    x = tf.random.normal(dims)
    hx_tf = tf_utils.fast_walsh_hadamard_transform(x)
    hhx_tf = tf_utils.fast_walsh_hadamard_transform(hx_tf)

    x, hx_tf, hhx_tf = self.evaluate([x, hx_tf, hhx_tf])
    self.assertAllEqual(x.shape, hhx_tf.shape)
    self.assertAllClose(x, hhx_tf)

  @parameterized.parameters([[1, 1], [4, 1], [2, 2], [1, 8], [1, 4]])
  def test_static_input_output_shape(self, *dims):
    """Tests static output shape is identical to static input shape."""
    x = tf.random.normal(dims)
    hx_tf = tf_utils.fast_walsh_hadamard_transform(x)
    hhx_tf = tf_utils.fast_walsh_hadamard_transform(hx_tf)
    self.assertEqual(list(dims), hx_tf.shape.as_list())
    self.assertEqual(list(dims), hhx_tf.shape.as_list())

  def test_dynamic_input_shape(self):
    """Tests dynamic input shape."""
    rand = tf.random.uniform((), maxval=4, dtype=tf.int32)
    x = tf.random.normal((3, 2**rand))
    hx_tf = tf_utils.fast_walsh_hadamard_transform(x)
    hhx_tf = tf_utils.fast_walsh_hadamard_transform(hx_tf)
    x, hx_tf, hhx_tf = self.evaluate([x, hx_tf, hhx_tf])
    self.assertAllEqual(x.shape, hhx_tf.shape)
    self.assertAllClose(x, hhx_tf)

  def test_dynamic_input_shape_dim_one(self):
    """Tests input shape where the second dimension is 1, dynamically known."""
    rand = tf.random.uniform((), maxval=1, dtype=tf.int32)
    x = tf.random.normal((3, 2**rand))
    hx_tf = tf_utils.fast_walsh_hadamard_transform(x)
    hhx_tf = tf_utils.fast_walsh_hadamard_transform(hx_tf)
    x, hx_tf, hhx_tf = self.evaluate([x, hx_tf, hhx_tf])
    self.assertAllEqual(x.shape, hhx_tf.shape)
    self.assertAllClose(x, hhx_tf)

  @parameterized.parameters([2, 4, 8, 16])
  def test_output_same_as_simple_python_implementation(self, dim):
    """Tests result is identical to inefficient implementation using scipy."""
    x = tf.random.normal([3, dim])
    hx_tf = tf_utils.fast_walsh_hadamard_transform(x)
    hhx_tf = tf_utils.fast_walsh_hadamard_transform(hx_tf)
    x, hx_tf, hhx_tf = self.evaluate([x, hx_tf, hhx_tf])

    hadamard_matrix = scipy.linalg.hadamard(dim)
    hx_py = np.dot(x, hadamard_matrix) / np.sqrt(dim)
    hhx_py = np.dot(hx_py, hadamard_matrix) / np.sqrt(dim)
    self.assertAllClose(hx_py, hx_tf)
    self.assertAllClose(hhx_py, hhx_tf)


class CMWCRandomSequenceTests(tf.test.TestCase, parameterized.TestCase):
  """Tests for `_cmwc_random_sequence` method."""

  @parameterized.parameters([1, 2, 99, 100, 101, 12345])
  def test_expected_output_shape(self, num_elements):
    sequence = tf_utils._cmwc_random_sequence(num_elements,
                                              tf.constant(123, tf.int64))
    self.assertAllEqual([num_elements], sequence.shape.as_list())
    self.assertEqual(tf.float64, sequence.dtype)
    sequence = self.evaluate(sequence)
    self.assertAllGreaterEqual(sequence, 0.0)
    self.assertAllLessEqual(sequence, 1.0)

  def test_deterministic_given_seed(self):
    sequence_1 = tf_utils._cmwc_random_sequence(10, tf.constant(123, tf.int64))
    sequence_2 = tf_utils._cmwc_random_sequence(10,
                                                tf.constant(120 + 3, tf.int64))
    sequence_1, sequence_2 = self.evaluate([sequence_1, sequence_2])
    self.assertAllEqual(sequence_1, sequence_2)

  def test_differs_given_different_seed(self):
    sequence_1 = tf_utils._cmwc_random_sequence(100, tf.constant(123, tf.int64))
    sequence_2 = tf_utils._cmwc_random_sequence(100, tf.constant(
        1234, tf.int64))
    sequence_1, sequence_2 = self.evaluate([sequence_1, sequence_2])
    self.assertFalse(np.array_equal(sequence_1, sequence_2))

  def test_approximately_uniform_distribution(self):
    sequence = tf_utils._cmwc_random_sequence(100000, tf.constant(
        123, tf.int64))
    sequence = self.evaluate(sequence)
    bucket_counts, _ = np.histogram(sequence, bins=10, range=(0, 1))
    self.assertAllGreaterEqual(bucket_counts, 9750)
    self.assertAllLessEqual(bucket_counts, 10250)

  def test_tensor_num_elements_raises(self):
    with self.assertRaisesRegex(TypeError, 'must be a Python integer'):
      tf_utils._cmwc_random_sequence(
          tf.constant(10), tf.constant(123, tf.int64))

  def test_negative_num_elements_raises(self):
    with self.assertRaisesRegex(ValueError, 'must be positive'):
      tf_utils._cmwc_random_sequence(-10, tf.constant(123, tf.int64))

  def test_python_seed_raises(self):
    with self.assertRaisesRegex(TypeError, 'tf.int64 Tensor'):
      tf_utils._cmwc_random_sequence(10, 123)

  def test_tf_int32_seed_raises(self):
    with self.assertRaisesRegex(TypeError, 'tf.int64 Tensor'):
      tf_utils._cmwc_random_sequence(10, tf.constant(123, tf.int32))


class RandomSignsCMWCTests(tf.test.TestCase, parameterized.TestCase):
  """Tests for `random_signs_cmwc` method."""

  @parameterized.parameters([1, 10, 101])
  def test_expected_output_values(self, num_elements):
    signs = tf_utils.random_signs_cmwc(num_elements, tf.constant(123, tf.int64))
    signs = self.evaluate(signs)
    self._assert_signs(signs)

  def test_both_values_present(self):
    signs = tf_utils.random_signs_cmwc(1000, tf.constant(123, tf.int64))
    signs = self.evaluate(signs)
    self._assert_signs(signs)
    self.assertGreater(sum(np.isclose(1.0, signs)), 400)
    self.assertGreater(sum(np.isclose(-1.0, signs)), 400)

  @parameterized.parameters([tf.float32, tf.float64, tf.int32, tf.int64])
  def test_expected_dtype(self, dtype):
    signs = tf_utils.random_signs_cmwc(10, tf.constant(123, tf.int64), dtype)
    self.assertEqual(dtype, signs.dtype)
    signs = self.evaluate(signs)
    self._assert_signs(signs)

  def test_differs_given_different_seed(self):
    signs_1 = tf_utils.random_signs_cmwc(100, tf.constant(123, tf.int64))
    signs_2 = tf_utils.random_signs_cmwc(100, tf.constant(1234, tf.int64))
    signs_1, signs_2 = self.evaluate([signs_1, signs_2])
    self.assertFalse(np.array_equal(signs_1, signs_2))

  def _assert_signs(self, x):
    size = len(x)
    self.assertAllEqual([True] * size,
                        np.logical_or(np.isclose(1.0, x), np.isclose(-1.0, x)))


class RandomFloatsCMWCTests(tf.test.TestCase, parameterized.TestCase):
  """Tests for `random_floats_cmwc` method."""

  @parameterized.parameters([tf.float32, tf.float64])
  def test_expected_dtype(self, dtype):
    floats = tf_utils.random_floats_cmwc(10, tf.constant(456, tf.int64), dtype)
    self.assertEqual(dtype, floats.dtype)

  @parameterized.parameters([tf.int32, tf.int64])
  def test_type_error_raises(self, dtype):
    with self.assertRaisesRegex(
        TypeError, 'Supported types are tf.float32 and tf.float64 values'
    ):
      tf_utils.random_floats_cmwc(10, tf.constant(456, tf.int64), dtype)

  def test_differs_given_different_seed(self):
    floats_1 = tf_utils.random_floats_cmwc(100, tf.constant(123, tf.int64))
    floats_2 = tf_utils.random_floats_cmwc(100, tf.constant(122, tf.int64))
    floats_1, floats_2 = self.evaluate([floats_1, floats_2])
    self.assertFalse(np.array_equal(floats_1, floats_2))


class RandomSignsTests(tf.test.TestCase, parameterized.TestCase):
  """Tests for `random_signs` method."""

  @parameterized.parameters([1, 10, 101])
  def test_expected_output_values(self, num_elements):
    signs = tf_utils.random_signs(num_elements, tf.constant([123, 456],
                                                            tf.int64))
    signs = self.evaluate(signs)
    self._assert_signs(signs)

  def test_both_values_present(self):
    signs = tf_utils.random_signs(1000, tf.constant([123, 456], tf.int64))
    signs = self.evaluate(signs)
    self._assert_signs(signs)
    self.assertGreater(sum(np.isclose(1.0, signs)), 400)
    self.assertGreater(sum(np.isclose(-1.0, signs)), 400)

  @parameterized.parameters([tf.float32, tf.float64, tf.int32, tf.int64])
  def test_expected_dtype(self, dtype):
    signs = tf_utils.random_signs(10, tf.constant([123, 456], tf.int64), dtype)
    self.assertEqual(dtype, signs.dtype)
    signs = self.evaluate(signs)
    self._assert_signs(signs)

  def test_differs_given_different_seed(self):
    signs_1 = tf_utils.random_signs(100, tf.constant([123, 456], tf.int64))
    signs_2 = tf_utils.random_signs(100, tf.constant([1234, 456], tf.int64))
    signs_1, signs_2 = self.evaluate([signs_1, signs_2])
    self.assertFalse(np.array_equal(signs_1, signs_2))

  def _assert_signs(self, x):
    size = len(x)
    self.assertAllEqual([True] * size,
                        np.logical_or(np.isclose(1.0, x), np.isclose(-1.0, x)))


class RandomFloatsTests(tf.test.TestCase, parameterized.TestCase):
  """Tests for `random_floats` method."""

  @parameterized.parameters([tf.float32, tf.float64])
  def test_expected_dtype(self, dtype):
    floats = tf_utils.random_floats(10, tf.constant([456, 123], tf.int64),
                                    dtype)
    self.assertEqual(dtype, floats.dtype)

  @parameterized.parameters([tf.int32, tf.int64])
  def test_type_error_raises(self, dtype):
    with self.assertRaisesRegex(
        TypeError, 'Supported types are tf.float32 and tf.float64 values'
    ):
      tf_utils.random_floats(10, tf.constant([456, 123], tf.int64), dtype)

  def test_differs_given_different_seed(self):
    floats_1 = tf_utils.random_floats(100, tf.constant([123, 456], tf.int64))
    floats_2 = tf_utils.random_floats(100, tf.constant([122, 456], tf.int64))
    floats_1, floats_2 = self.evaluate([floats_1, floats_2])
    self.assertFalse(np.array_equal(floats_1, floats_2))


class PackingUtilsTests(tf.test.TestCase, parameterized.TestCase):
  """Tests for bit-packing utilities."""

  @parameterized.parameters(
      itertools.product([
          (1, [[1 + 4 + 8]]),
          (2, [[1 + 4**2 + 4**3]]),
          (3, [[1 + 8**2 + 8**3]]),
          (4, [[1 + 16**2 + 16**3]]),
          (8, [[16842753], [0]])
      ], [tf.int32, tf.int64])
      )
  def test_pack_into_int(self, test_values, dtype):
    input_bitrange, expected_packed_value = test_values
    value = tf.constant([1, 0, 1, 1, 0], dtype)
    packed_value = tf_utils.pack_into_int(
        value, input_bitrange, target_bitrange=28)
    self.assertEqual(dtype, packed_value.dtype)
    self.assertAllEqual(expected_packed_value, self.evaluate(packed_value))

  @parameterized.parameters(
      itertools.product([
          (1, [[1 + 4 + 8]]),
          (2, [[1 + 4**2 + 4**3]]),
          (3, [[1 + 8**2 + 8**3]]),
          (4, [[1 + 16**2 + 16**3]]),
          (8, [[16842753], [0]])
      ], [tf.int32, tf.int64])
      )
  def test_unpack_from_int(self, test_values, dtype):
    original_bitrange, packed_value = test_values
    packed_value = tf.constant(packed_value, dtype)
    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange, target_bitrange=28, shape=(5,))
    self.assertEqual(dtype, unpacked_value.dtype)
    self.assertAllEqual([1, 0, 1, 1, 0], self.evaluate(unpacked_value))

  def test_unpack_from_int_different_outputs(self):
    packed_value = tf.constant([[1 + 2**3]], tf.int32)

    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=1, target_bitrange=28, shape=(4,))
    self.assertAllEqual([1, 0, 0, 1], self.evaluate(unpacked_value))

    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=1, target_bitrange=28, shape=(5,))
    self.assertAllEqual([1, 0, 0, 1, 0], self.evaluate(unpacked_value))

    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=2, target_bitrange=28, shape=(2,))
    self.assertAllEqual([1, 2], self.evaluate(unpacked_value))

    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=2, target_bitrange=28, shape=(3,))
    self.assertAllEqual([1, 2, 0], self.evaluate(unpacked_value))

    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=3, target_bitrange=28, shape=(2,))
    self.assertAllEqual([1, 1], self.evaluate(unpacked_value))

    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=3, target_bitrange=28, shape=(3,))
    self.assertAllEqual([1, 1, 0], self.evaluate(unpacked_value))

    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=4, target_bitrange=28, shape=(1,))
    self.assertAllEqual([9], self.evaluate(unpacked_value))

    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=4, target_bitrange=28, shape=(2,))
    self.assertAllEqual([9, 0], self.evaluate(unpacked_value))

  @parameterized.parameters([(1, 28), (2, 28), (6, 28), (7, 28), (8, 28),
                             (12, 28)])
  def test_boundary_conditions(self, input_bitrange, target_bitrange):
    max_v = 2**input_bitrange - 1
    input_value = tf.constant(
        [0, 0, 0, max_v, max_v, max_v, 0, 0, max_v, max_v, 0, max_v] * 20)

    for length in [1, 6, 7, 8, 20*6, 20*7, 20*8, 20*12]:
      value = input_value[:length]
      packed_value = tf_utils.pack_into_int(value, input_bitrange,
                                            target_bitrange)
      unpacked_value = tf_utils.unpack_from_int(packed_value, input_bitrange,
                                                target_bitrange, value.shape)

    self.assertAllEqual(self.evaluate(value), self.evaluate(unpacked_value))

  @parameterized.parameters([(1, 28), (2, 28), (6, 28), (7, 28), (8, 28),
                             (12, 28)])
  def test_random_input(self, input_bitrange, target_bitrange):
    # Tests that packing/unpacking amounts to identity, regardless of the input.
    num_elements = np.random.randint(low=1, high=50)
    value = tf.constant(
        np.random.randint(low=0, high=2**input_bitrange, size=num_elements))
    packed_value = tf_utils.pack_into_int(value, input_bitrange,
                                          target_bitrange)
    unpacked_value = tf_utils.unpack_from_int(packed_value, input_bitrange,
                                              target_bitrange, value.shape)

    value, unpacked_value = self.evaluate((value, unpacked_value))
    try:
      self.assertAllEqual(value, unpacked_value)
    except:  # pylint: disable=bare-except
      self.fail(f'Random input test failed with input value: {value}')

  def test_pack_into_int_special_case_6_28(self):
    value = tf.constant(
        [50, 19, 51, 59, 10, 53, 36, 44, 31, 44, 31, 10, 31, 56, 49, 48, 35])
    packed_value = tf_utils.pack_into_int(
        value, input_bitrange=6, target_bitrange=28)
    expected_packed_value = tf.constant([[183448818], [33236180], [236923387],
                                         [146481]])
    self.assertAllEqual(self.evaluate(expected_packed_value),
                        self.evaluate(packed_value))

  def test_unpack_from_int_special_case_6_28(self):
    packed_value = tf.constant([[183448818], [33236180], [236923387], [146481]])
    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=6, target_bitrange=28, shape=(17,))
    expected_unpacked_value = tf.constant(
        [50, 19, 51, 59, 10, 53, 36, 44, 31, 44, 31, 10, 31, 56, 49, 48, 35])
    self.assertAllEqual(self.evaluate(expected_unpacked_value),
                        self.evaluate(unpacked_value))

  def test_pack_into_int_special_case_7_28(self):
    value = tf.constant([117, 86, 42, 69, 9, 70, 66, 8, 112, 116])
    packed_value = tf_utils.pack_into_int(
        value, input_bitrange=7, target_bitrange=28)
    expected_packed_value = tf.constant([[145402741], [17867529], [14960]])
    self.assertAllEqual(self.evaluate(expected_packed_value),
                        self.evaluate(packed_value))

  def test_unpack_from_int_special_case_7_28(self):
    packed_value = tf.constant([[145402741], [17867529], [14960]])
    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=7, target_bitrange=28, shape=(10,))
    expected_unpacked_value = tf.constant(
        [117, 86, 42, 69, 9, 70, 66, 8, 112, 116])
    self.assertAllEqual(self.evaluate(expected_unpacked_value),
                        self.evaluate(unpacked_value))

  def test_pack_into_int_special_case_8_28(self):
    value = tf.constant([38, 147, 1, 201, 205, 36, 155, 78, 163, 98])
    packed_value = tf_utils.pack_into_int(
        value, input_bitrange=8, target_bitrange=28)
    expected_packed_value = tf.constant([[151098150], [162680028], [6464334]])
    self.assertAllEqual(self.evaluate(expected_packed_value),
                        self.evaluate(packed_value))

  def test_unpack_from_int_special_case_8_28(self):
    packed_value = tf.constant([[151098150], [162680028], [6464334]])
    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=8, target_bitrange=28, shape=(10,))
    expected_unpacked_value = tf.constant(
        [38, 147, 1, 201, 205, 36, 155, 78, 163, 98])
    self.assertAllEqual(self.evaluate(expected_unpacked_value),
                        self.evaluate(unpacked_value))

  def test_pack_into_int_special_case_12_28(self):
    value = tf.constant(
        [2805, 3264, 2344, 3472, 2962, 768, 2867, 3703, 2883, 2406])
    packed_value = tf_utils.pack_into_int(
        value, input_bitrange=12, target_bitrange=28)
    expected_packed_value = tf.constant(
        [[147589877], [153981074], [187904011], [112475767], [150]])
    self.assertAllEqual(self.evaluate(expected_packed_value),
                        self.evaluate(packed_value))

  def test_unpack_from_int_special_case_12_28(self):
    packed_value = tf.constant(
        [[147589877], [153981074], [187904011], [112475767], [150]])
    unpacked_value = tf_utils.unpack_from_int(
        packed_value, original_bitrange=12, target_bitrange=28, shape=(10,))
    expected_unpacked_value = tf.constant(
        [2805, 3264, 2344, 3472, 2962, 768, 2867, 3703, 2883, 2406])
    self.assertAllEqual(self.evaluate(expected_unpacked_value),
                        self.evaluate(unpacked_value))


if __name__ == '__main__':
  tf.test.main()
