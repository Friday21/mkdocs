#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals

import mock
import os
import unittest
import tempfile
import shutil
import stat

from mkdocs import nav, utils, exceptions
from mkdocs.tests.base import dedent, load_config
from mkdocs.utils.ghp_import import dec


class UtilsTests(unittest.TestCase):
    def test_html_path(self):
        expected_results = {
            'index.md': 'index.html',
            'api-guide.md': 'api-guide/index.html',
            'api-guide/index.md': 'api-guide/index.html',
            'api-guide/testing.md': 'api-guide/testing/index.html',
        }
        for file_path, expected_html_path in expected_results.items():
            html_path = utils.get_html_path(file_path)
            self.assertEqual(html_path, expected_html_path)

    def test_url_path(self):
        expected_results = {
            'index.md': '/',
            'api-guide.md': '/api-guide/',
            'api-guide/index.md': '/api-guide/',
            'api-guide/testing.md': '/api-guide/testing/',
        }
        for file_path, expected_html_path in expected_results.items():
            html_path = utils.get_url_path(file_path)
            self.assertEqual(html_path, expected_html_path)

    def test_is_markdown_file(self):
        expected_results = {
            'index.md': True,
            'index.MARKDOWN': True,
            'index.txt': False,
            'indexmd': False
        }
        for path, expected_result in expected_results.items():
            is_markdown = utils.is_markdown_file(path)
            self.assertEqual(is_markdown, expected_result)

    def test_is_html_file(self):
        expected_results = {
            'index.htm': True,
            'index.HTML': True,
            'index.txt': False,
            'indexhtml': False
        }
        for path, expected_result in expected_results.items():
            is_html = utils.is_html_file(path)
            self.assertEqual(is_html, expected_result)

    def test_create_media_urls(self):
        pages = [
            {'Home': 'index.md'},
            {'About': 'about.md'},
            {'Sub': [
                {'Sub Home': 'index.md'},
                {'Sub About': 'about.md'},

            ]}
        ]
        expected_results = {
            'https://media.cdn.org/jq.js': 'https://media.cdn.org/jq.js',
            'http://media.cdn.org/jquery.js': 'http://media.cdn.org/jquery.js',
            '//media.cdn.org/jquery.js': '//media.cdn.org/jquery.js',
            'media.cdn.org/jquery.js': './media.cdn.org/jquery.js',
            'local/file/jquery.js': './local/file/jquery.js',
            'image.png': './image.png',
        }
        site_navigation = nav.SiteNavigation(load_config(pages=pages))
        for path, expected_result in expected_results.items():
            urls = utils.create_media_urls(site_navigation, [path])
            self.assertEqual(urls[0], expected_result)

    def test_create_relative_media_url_sub_index(self):
        '''
        test special case where there's a sub/index.md page
        '''

        pages = [
            {'Home': 'index.md'},
            {'Sub': [
                {'Sub Home': '/subpage/index.md'},

            ]}
        ]
        site_navigation = nav.SiteNavigation(load_config(pages=pages))
        site_navigation.url_context.set_current_url('/subpage/')
        site_navigation.file_context.current_file = "subpage/index.md"

        def assertPathGenerated(declared, expected):
            url = utils.create_relative_media_url(site_navigation, declared)
            self.assertEqual(url, expected)

        assertPathGenerated("img.png", "./img.png")
        assertPathGenerated("./img.png", "./img.png")
        assertPathGenerated("/img.png", "../img.png")

    def test_create_relative_media_url_sub_index_windows(self):
        '''
        test special case where there's a sub/index.md page and we are on Windows.
        current_file paths uses backslash in Windows
        '''

        pages = [
            {'Home': 'index.md'},
            {'Sub': [
                {'Sub Home': '/level1/level2/index.md'},

            ]}
        ]
        site_navigation = nav.SiteNavigation(load_config(pages=pages))
        site_navigation.url_context.set_current_url('/level1/level2')
        site_navigation.file_context.current_file = "level1\\level2\\index.md"

        def assertPathGenerated(declared, expected):
            url = utils.create_relative_media_url(site_navigation, declared)
            self.assertEqual(url, expected)

        assertPathGenerated("img.png", "./img.png")
        assertPathGenerated("./img.png", "./img.png")
        assertPathGenerated("/img.png", "../img.png")

    def test_reduce_list(self):
        self.assertEqual(
            utils.reduce_list([1, 2, 3, 4, 5, 5, 2, 4, 6, 7, 8]),
            [1, 2, 3, 4, 5, 6, 7, 8]
        )

    def test_get_themes(self):

        self.assertEqual(
            sorted(utils.get_theme_names()),
            ['mkdocs', 'readthedocs'])

    @mock.patch('pkg_resources.iter_entry_points', autospec=True)
    def test_get_theme_dir(self, mock_iter):

        path = 'some/path'

        theme = mock.Mock()
        theme.name = 'mkdocs2'
        theme.dist.key = 'mkdocs2'
        theme.load().__file__ = os.path.join(path, '__init__.py')

        mock_iter.return_value = iter([theme])

        self.assertEqual(utils.get_theme_dir(theme.name), os.path.abspath(path))

    def test_get_theme_dir_keyerror(self):

        self.assertRaises(KeyError, utils.get_theme_dir, 'nonexistanttheme')

    @mock.patch('pkg_resources.iter_entry_points', autospec=True)
    def test_get_theme_dir_importerror(self, mock_iter):

        theme = mock.Mock()
        theme.name = 'mkdocs2'
        theme.dist.key = 'mkdocs2'
        theme.load.side_effect = ImportError()

        mock_iter.return_value = iter([theme])

        self.assertRaises(ImportError, utils.get_theme_dir, theme.name)

    @mock.patch('pkg_resources.iter_entry_points', autospec=True)
    def test_get_themes_warning(self, mock_iter):

        theme1 = mock.Mock()
        theme1.name = 'mkdocs2'
        theme1.dist.key = 'mkdocs2'
        theme1.load().__file__ = "some/path1"

        theme2 = mock.Mock()
        theme2.name = 'mkdocs2'
        theme2.dist.key = 'mkdocs3'
        theme2.load().__file__ = "some/path2"

        mock_iter.return_value = iter([theme1, theme2])

        self.assertEqual(
            sorted(utils.get_theme_names()),
            sorted(['mkdocs2', ]))

    @mock.patch('pkg_resources.iter_entry_points', autospec=True)
    @mock.patch('pkg_resources.get_entry_map', autospec=True)
    def test_get_themes_error(self, mock_get, mock_iter):

        theme1 = mock.Mock()
        theme1.name = 'mkdocs'
        theme1.dist.key = 'mkdocs'
        theme1.load().__file__ = "some/path1"

        theme2 = mock.Mock()
        theme2.name = 'mkdocs'
        theme2.dist.key = 'mkdocs2'
        theme2.load().__file__ = "some/path2"

        mock_iter.return_value = iter([theme1, theme2])
        mock_get.return_value = {'mkdocs': theme1, }

        self.assertRaises(exceptions.ConfigurationError, utils.get_theme_names)

    def test_nest_paths(self):

        j = os.path.join

        result = utils.nest_paths([
            'index.md',
            j('user-guide', 'configuration.md'),
            j('user-guide', 'styling-your-docs.md'),
            j('user-guide', 'writing-your-docs.md'),
            j('about', 'contributing.md'),
            j('about', 'license.md'),
            j('about', 'release-notes.md'),
        ])

        self.assertEqual(
            result,
            [
                'index.md',
                {'User guide': [
                    j('user-guide', 'configuration.md'),
                    j('user-guide', 'styling-your-docs.md'),
                    j('user-guide', 'writing-your-docs.md')]},
                {'About': [
                    j('about', 'contributing.md'),
                    j('about', 'license.md'),
                    j('about', 'release-notes.md')]}
            ]
        )

    def test_unicode_yaml(self):

        yaml_src = dedent(
            '''
            key: value
            key2:
              - value
            '''
        )

        config = utils.yaml_load(yaml_src)
        self.assertTrue(isinstance(config['key'], utils.text_type))
        self.assertTrue(isinstance(config['key2'][0], utils.text_type))

    def test_copy_files(self):
        src_paths = [
            'foo.txt',
            'bar.txt',
            'baz.txt',
        ]
        dst_paths = [
            'foo.txt',
            'foo/',             # ensure src filename is appended
            'foo/bar/baz.txt'   # ensure missing dirs are created
        ]
        expected = [
            'foo.txt',
            'foo/bar.txt',
            'foo/bar/baz.txt',
        ]

        src_dir = tempfile.mkdtemp()
        dst_dir = tempfile.mkdtemp()

        try:
            for i, src in enumerate(src_paths):
                src = os.path.join(src_dir, src)
                with open(src, 'w') as f:
                    f.write('content')
                dst = os.path.join(dst_dir, dst_paths[i])
                utils.copy_file(src, dst)
                self.assertTrue(os.path.isfile(os.path.join(dst_dir, expected[i])))
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dst_dir)

    def test_copy_files_without_permissions(self):
        src_paths = [
            'foo.txt',
            'bar.txt',
            'baz.txt',
        ]
        expected = [
            'foo.txt',
            'bar.txt',
            'baz.txt',
        ]

        src_dir = tempfile.mkdtemp()
        dst_dir = tempfile.mkdtemp()

        try:
            for i, src in enumerate(src_paths):
                src = os.path.join(src_dir, src)
                with open(src, 'w') as f:
                    f.write('content')
                # Set src file to read-only
                os.chmod(src, stat.S_IRUSR)
                utils.copy_file(src, dst_dir)
                self.assertTrue(os.path.isfile(os.path.join(dst_dir, expected[i])))
                self.assertNotEqual(os.stat(src).st_mode, os.stat(os.path.join(dst_dir, expected[i])).st_mode)
                # While src was read-only, dst must remain writable
                self.assertTrue(os.access(os.path.join(dst_dir, expected[i]), os.W_OK))
        finally:
            for src in src_paths:
                # Undo read-only so we can delete temp files
                src = os.path.join(src_dir, src)
                if os.path.exists(src):
                    os.chmod(src, stat.S_IRUSR | stat.S_IWUSR)
            shutil.rmtree(src_dir)
            shutil.rmtree(dst_dir)

    def test_unicode_clean_directory(self):
        temp_dir = tempfile.mkdtemp()
        utf8_temp_dir = os.path.join(dec('tmp'), dec('tmp_utf8'))

        utf8_directory = os.path.join(utf8_temp_dir, '导航')
        utf8_utf8_directory = os.path.join(utf8_directory, '导航')
        ascii_directory = os.path.join(temp_dir, 'bar')
        ascii_ascii_directory = os.path.join(ascii_directory, 'bar')

        os.makedirs(utf8_utf8_directory)
        os.makedirs(ascii_ascii_directory)

        utf_8_path = os.path.join(utf8_utf8_directory, 'foo.txt')
        ascii_path = os.path.join(ascii_ascii_directory, 'foo.txt')

        with open(utf_8_path, 'w') as f:
            f.write('content')

        with open(ascii_path, 'w') as f:
            f.write('content')

        try:
            utils.clean_directory(utf8_directory)
            utils.clean_directory(ascii_directory)
            self.assertFalse(os.path.exists(utf_8_path))
            self.assertFalse(os.path.exists(ascii_path))
            self.assertFalse(os.path.exists(utf8_utf8_directory))
            self.assertFalse(os.path.exists(ascii_ascii_directory))
        finally:
            shutil.rmtree(temp_dir)
            shutil.rmtree(utf8_temp_dir)
