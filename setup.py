#!/usr/bin/env python3
"""
Setup script for 3D Bone Segmentation Application

This script allows the project to be installed as a package,
making it easier to distribute and manage dependencies.
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "3D Bone Segmentation Application for medical imaging visualization"

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    requirements = []
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Remove version constraints for setup.py (optional)
                    # You can keep them if you want strict version control
                    requirements.append(line)
    return requirements

setup(
    name="bone-segmentation-3d",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A comprehensive medical imaging application for 3D bone segmentation and visualization",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/Bone_Segmentation-3D",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Scientific/Engineering :: Image Processing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest",
            "black",
            "flake8",
            "mypy",
        ],
        "docs": [
            "sphinx",
            "sphinx-rtd-theme",
        ]
    },
    entry_points={
        "console_scripts": [
            "bone-segmentation-3d=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    keywords=[
        "medical-imaging", 
        "3d-visualization", 
        "bone-segmentation", 
        "dicom", 
        "ct-scan", 
        "mayavi", 
        "vtk", 
        "pyqt5",
        "medical-software",
        "image-processing"
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/Bone_Segmentation-3D/issues",
        "Source": "https://github.com/yourusername/Bone_Segmentation-3D",
        "Documentation": "https://github.com/yourusername/Bone_Segmentation-3D/wiki",
    }
)