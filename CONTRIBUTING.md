# Contributing to Bone Segmentation 3D

Thank you for your interest in contributing to this project! This medical imaging application was developed as part of an MSc thesis in Biomedical Engineering and continues to evolve with community contributions.

## Getting Started

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/3D-Bone-Segmentation.git
   cd 3D-Bone-Segmentation
   ```

2. **Create a conda environment**
   ```bash
   conda create -n bone3d-dev python=3.10 -y
   conda activate bone3d-dev
   conda install -c conda-forge mayavi vtk pyqt -y
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests**
   ```bash
   pytest tests/
   ```

## Project Structure

```
src/bone_segmentation/
├── core/           # Image processing and data handling
├── ui/             # PyQt5 user interface components
└── visualization/  # Mayavi 3D visualization
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for public functions and classes
- Format code with `black`: `black src/ tests/`
- Sort imports with `isort`: `isort src/ tests/`

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with clear, atomic commits

3. **Run tests and linting**
   ```bash
   pytest tests/
   black --check src/ tests/
   flake8 src/ tests/
   ```

4. **Submit a pull request** with:
   - Clear description of changes
   - Any related issue numbers
   - Screenshots for UI changes

## Types of Contributions

### Bug Reports
- Use the issue tracker
- Include steps to reproduce
- Provide system information (OS, Python version, etc.)

### Feature Requests
- Open an issue to discuss first
- Describe the use case and benefit

### Code Contributions
- Bug fixes
- New features (discussed via issue first)
- Documentation improvements
- Test coverage improvements

### Clinical Input
We especially welcome feedback from:
- Medical professionals
- Biomedical engineers
- Healthcare technology researchers

## Testing

- Write tests for new features in `tests/`
- Ensure existing tests pass
- Aim for good coverage of critical paths

## Questions?

Feel free to open an issue for questions or discussions about the project.
