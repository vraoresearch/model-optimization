load("//tensorflow_model_optimization:tensorflow_model_optimization.bzl", "py_strict_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])

py_strict_library(
    name = "core",
    srcs = ["__init__.py"],
    deps = [
        "//tensorflow_model_optimization/python/core/api",  # buildcleaner: keep
        "//tensorflow_model_optimization/python/core/clustering",  # buildcleaner: keep
        "//tensorflow_model_optimization/python/core/internal",  # buildcleaner: keep
        "//tensorflow_model_optimization/python/core/keras",  # buildcleaner: keep
        "//tensorflow_model_optimization/python/core/quantization",  # buildcleaner: keep
        "//tensorflow_model_optimization/python/core/sparsity",  # buildcleaner: keep
    ],
)

py_strict_library(
    name = "version",
    srcs = ["version.py"],
)
