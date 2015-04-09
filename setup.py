from setuptools import setup


with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [
    'aiohttp',
    'arrow',
    'CairoSVG',
    'cssselect',
    'flask',
    'lxml',
    'pygal',
    'python-redmine',
    'tinycss',
]

setup(
    name='redmine-charts-images',
    version='0.1.0',
    description='Display meaningful Redmine charts.',
    long_description=readme,
    author="Sviatoslav Abakumov",
    author_email='dust.harvesting@gmail.com',
    url='https://github.com/perlence/redmine-charts-images',
    packages=[
        'redminecharts',
    ],
    package_dir={
        'redminecharts': 'redminecharts'
    },
    include_package_data=True,
    install_requires=requirements,
    license='BSD',
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'redminecharts = redminecharts.redminecharts:main'
        ],
    },
    keywords='redmine-charts-images',
    classifiers=[
        'Development Status :: 2 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
)
