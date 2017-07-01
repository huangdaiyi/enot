import os
import unittest
from os.path import join

from mock import patch, PropertyMock

import test
from coon.__main__ import create
from coon.pac_cache.local_cache import LocalCache
from coon.packages.package import Package
from coon.packages.package_builder import Builder
from coon.packages.package_controller import Controller
from coon.utils.file_utils import remove_dir, ensure_dir
from test.abs_test_class import TestClass, modify_config, set_git_url, set_git_tag, set_deps


def mock_fetch_package(dep: Package):
    test_dir = test.get_test_dir('controller_tests')
    tmp_path = join(os.getcwd(), test_dir, 'tmp')
    dep.update_from_cache(join(tmp_path, dep.name))


class ControllerTests(TestClass):
    def __init__(self, method_name):
        super().__init__('controller_tests', method_name)

    def setUp(self):
        super().setUp()
        ensure_dir(join(self.test_dir, 'conf'))

    # Test if package can be installed via install actions
    @patch('coon.global_properties.GlobalProperties.conf_dir', new_callable=PropertyMock)
    @patch('coon.global_properties.ensure_conf_file')
    def test_install_package(self, mock_conf, mock_conf_dir):
        mock_conf.return_value = self.conf_file
        mock_conf_dir.return_value = join(self.test_dir, 'conf')
        # create package, fill config with install steps
        create(self.test_dir, {'<name>': 'test_app'})
        pack_path = join(self.test_dir, 'test_app')
        set_git_url(pack_path, 'http://github/comtihon/test_app')
        set_git_tag(pack_path, '1.0.0')
        test_install_dir = join(self.test_dir, 'test_install')
        modify_config(pack_path,
                      {'install':
                          [
                              {'shell': 'mkdir ' + test_install_dir},
                              {'shell': 'cp ebin/*.* ' + test_install_dir}
                          ]})
        builder = self.__add_to_local(pack_path)
        controller = Controller()
        self.assertEqual(True, controller.local_cache.exists(builder.project))
        self.assertEqual(False, os.path.isdir(test_install_dir))
        # install and check installed actions result
        self.assertEqual(True, controller.install('comtihon/test_app', None))
        self.assertEqual(True, os.path.isdir(test_install_dir))
        installed = os.listdir(test_install_dir)
        self.assertEqual(['test_app.app', 'test_app_app.beam', 'test_app_sup.beam'], sorted(installed))

    # Test if package can be uninstalled via uninstall actions
    @patch('coon.global_properties.GlobalProperties.conf_dir', new_callable=PropertyMock)
    @patch('coon.global_properties.ensure_conf_file')
    def test_uninstall_package(self, mock_conf, mock_conf_dir):
        mock_conf.return_value = self.conf_file
        mock_conf_dir.return_value = join(self.test_dir, 'conf')
        # create package, fill config with install steps
        create(self.test_dir, {'<name>': 'test_app'})
        pack_path = join(self.test_dir, 'test_app')
        set_git_url(pack_path, 'http://github/comtihon/test_app')
        set_git_tag(pack_path, '1.0.0')
        test_install_dir = join(self.test_dir, 'test_install')
        modify_config(pack_path,
                      {
                          'install':
                              [
                                  {'shell': 'mkdir ' + test_install_dir},
                                  {'shell': 'cp ebin/*.* ' + test_install_dir}
                              ],
                          'uninstall':
                              [
                                  {'shell': 'rm -rf ' + test_install_dir}
                              ]
                      })
        self.__add_to_local(pack_path)
        controller = Controller()
        self.assertEqual(True, controller.install('comtihon/test_app', None))
        self.assertEqual(True, os.path.isdir(test_install_dir))
        self.assertEqual(True, controller.uninstall('comtihon/test_app'))
        self.assertEqual(False, os.path.isdir(test_install_dir))

    # Test if all installed packages are listed
    @patch('coon.global_properties.GlobalProperties.conf_dir', new_callable=PropertyMock)
    @patch('coon.global_properties.ensure_conf_file')
    def test_list_installed(self, mock_conf, mock_conf_dir):
        mock_conf.return_value = self.conf_file
        mock_conf_dir.return_value = join(self.test_dir, 'conf')
        apps = ['test_app', 'test_app1', 'test_app2']
        # create packages, fill config with install steps
        for name in apps:
            create(self.test_dir, {'<name>': name})
            pack_path = join(self.test_dir, name)
            set_git_url(pack_path, 'http://github/comtihon/' + name)
            set_git_tag(pack_path, '1.0.0')
            test_install_dir = join(self.test_dir, 'test_install_' + name)
            modify_config(pack_path,
                          {'install':
                              [
                                  {'shell': 'mkdir ' + test_install_dir},
                                  {'shell': 'cp ebin/*.* ' + test_install_dir}
                              ]})
            self.__add_to_local(pack_path)
            self.assertEqual(True, Controller().install('comtihon/' + name, None))
        installed_expected = [{'name': 'comtihon/' + app, 'vsn': '1.0.0'} for app in apps]
        self.assertEqual(installed_expected, Controller().installed())

    # Test installing package with deps. Deps can be used in shell scripts.
    @patch.object(LocalCache, 'fetch_package', side_effect=mock_fetch_package)
    @patch('coon.global_properties.GlobalProperties.conf_dir', new_callable=PropertyMock)
    @patch('coon.global_properties.ensure_conf_file')
    def test_install_with_deps(self, mock_conf, mock_conf_dir, _):
        mock_conf.return_value = self.conf_file
        mock_conf_dir.return_value = join(self.test_dir, 'conf')
        # Create test_app with deps: A and B
        create(self.test_dir, {'<name>': 'test_app'})
        pack_path = join(self.test_dir, 'test_app')
        set_git_url(pack_path, 'http://github/comtihon/test_app')
        set_git_tag(pack_path, '1.0.0')
        set_deps(pack_path,
                 [
                     {'name': 'a_with_dep_a2',
                      'url': 'https://github.com/comtihon/a_with_dep_a2',
                      'tag': '1.0.0'},
                     {'name': 'b_with_no_deps',
                      'url': 'https://github.com/comtihon/b_with_no_deps',
                      'tag': '1.0.0'}
                 ])
        test_install_dir = join(self.test_dir, 'test_install')
        modify_config(pack_path,
                      {'install':
                          [
                              {'shell': 'mkdir ' + test_install_dir},
                              {'shell': 'cp ebin/*.* ' + test_install_dir},
                              {'shell': 'cp deps/*/ebin/*.* ' + test_install_dir},
                          ]
                      })
        # Create dep A with dep A2 (in tmp, as if we download them from git)
        create(self.tmp_dir, {'<name>': 'a_with_dep_a2'})
        dep_a1_path = join(self.tmp_dir, 'a_with_dep_a2')
        set_deps(dep_a1_path, [{'name': 'a2_with_no_deps',
                                'url': 'https://github.com/comtihon/a2_with_no_deps',
                                'tag': '1.0.0'}])
        set_git_url(dep_a1_path, 'http://github/comtihon/a2_with_no_deps')
        set_git_tag(dep_a1_path, '1.0.0')
        # Create dep B (in tmp, as if we download them from git)
        create(self.tmp_dir, {'<name>': 'b_with_no_deps'})
        dep_b_path = join(self.tmp_dir, 'b_with_no_deps')
        set_git_url(dep_b_path, 'http://github/comtihon/b_with_no_deps')
        set_git_tag(dep_b_path, '1.0.0')
        # Create dep A2 (in tmp, as if we download them from git)
        create(self.tmp_dir, {'<name>': 'a2_with_no_deps'})
        dep_a2_path = join(self.tmp_dir, 'a2_with_no_deps')
        set_git_url(dep_a2_path, 'http://github/comtihon/a2_with_no_deps')
        set_git_tag(dep_a2_path, '1.0.0')
        # Compile test_project, add to local cache
        self.__add_to_local(pack_path)
        self.assertEqual(True, Controller().install('comtihon/test_app', None))
        self.assertEqual(True, os.path.isdir(test_install_dir))
        installed = os.listdir(test_install_dir)
        expected = ['a2_with_no_deps.app',
                    'a2_with_no_deps_app.beam',
                    'a2_with_no_deps_sup.beam',
                    'a_with_dep_a2.app',
                    'a_with_dep_a2_app.beam',
                    'a_with_dep_a2_sup.beam',
                    'b_with_no_deps.app',
                    'b_with_no_deps_app.beam',
                    'b_with_no_deps_sup.beam',
                    'test_app.app',
                    'test_app_app.beam',
                    'test_app_sup.beam']
        self.assertEqual(expected, sorted(installed))

    def __add_to_local(self, pack_path):
        builder = Builder.init_from_path(pack_path)
        builder.populate()
        self.assertEqual(True, builder.build())
        controller = Controller()
        self.assertEqual(True, controller.local_cache.add_package(builder.project))
        return builder

    def tearDown(self):
        super().tearDown()
        remove_dir(join(self.test_dir, 'conf'))


if __name__ == '__main__':
    unittest.main()
