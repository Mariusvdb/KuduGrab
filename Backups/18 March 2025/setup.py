from setuptools import setup

setup(
    name="screen_capture",
    version="1.0.0",
    description="Portable Screen Capture Tool for Windows",
    author="Your Name",
    packages=[""],
    install_requires=[
        "PyQt5>=5.15.0",
        "Pillow>=9.0.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "screencap=screen_capture_app:main",
        ],
    },
)