import os
import shutil
from os.path import join

from git import Repo

from walrus.pac_cache import Cache
from walrus.packages.package import Package
from walrus.utils.file_utils import if_dir_exists, ensure_dir, link_if_needed
from walrus.utils.file_utils import remove_dir


class LocalCache(Cache):
    def __init__(self, temp_dir, cache_url):
        path = cache_url[7:]
        super().__init__(temp_dir, path)
        if not os.path.exists(path):
            os.makedirs(path)

    def exists(self, package: Package) -> bool:
        return if_dir_exists(self.path, self.__get_package_path(package))

    # clone git repo to tmp, make package to scan and update it's config
    def fetch_package(self, package: Package):
        temp_path = join(self.temp_dir, package.get_name())
        print('fetch ' + temp_path)
        remove_dir(temp_path)
        repo = Repo.clone_from(package.url, temp_path)
        assert not repo.bare
        git = repo.git
        git.checkout(package.vsn)
        repo.create_head(package.vsn)
        LocalCache.fill_package_from_temp(package, temp_path)

    # make package to scan and update it's config
    def get_package(self, package: Package):
        LocalCache.fill_package_from_temp(package, join(self.temp_dir, package.get_name()))

    # add built package to local cache
    def add_package(self, package: Package, rewrite=False):
        full_dir = join(self.path, self.__get_package_path(package))
        ensure_dir(full_dir)
        print('add ' + package.get_name())
        path = package.config.path
        LocalCache.__copy_data(rewrite, full_dir, path, 'ebin')
        LocalCache.__copy_include(rewrite, full_dir, path)
        if package.config.with_source:
            LocalCache.__copy_data(rewrite, full_dir, path, 'src')
        if package.config.with_source and package.config.has_nifs:
            LocalCache.__copy_data(rewrite, full_dir, path, 'c_src')

    # link package from local cache to project
    def link_package(self, package: Package, path: str):
        if not path:
            path = os.getcwd()
        package_path = join(self.path, self.__get_package_path(package))
        package_name = package.get_name()
        dep_dir = join(path, 'deps', package_name)
        ensure_dir(dep_dir)
        print('link ' + package_name)
        LocalCache.link(package_path, path, package_name, 'include')
        LocalCache.link(package_path, path, package_name, 'src')
        LocalCache.link(package_path, path, package_name, 'ebin')
        if package.config.has_nifs:
            LocalCache.link(package_path, path, package_name, 'priv')

    def __get_package_path(self, package: Package):
        namespace = package.url.split('/')[-2]
        return join(package.get_name(), namespace, package.vsn, self.erlang_version)

    @staticmethod
    def fill_package_from_temp(package: Package, path: str):
        package.fill_from_path(path)

    @staticmethod
    def link(package_path, current_dir, name, dir_to_link):
        include_src = join(package_path, dir_to_link)
        include_dst = join(current_dir, 'deps', name, dir_to_link)
        link_if_needed(include_src, include_dst)

    @staticmethod
    def __copy_include(rewrite, full_dir, path):
        cache_include = join(full_dir, 'include')
        if rewrite or not os.path.exists(cache_include):
            package_include = join(path, 'include')
            if os.path.exists(package_include):
                print('copy ' + package_include + ' to' + cache_include)
                shutil.copytree(package_include, cache_include)

    @staticmethod
    def __copy_data(rewrite, full_dir, path, source_dir):
        cache_src = join(full_dir, source_dir)
        if rewrite or not os.path.exists(cache_src):
            package_src = join(path, source_dir)
            print('copy ' + package_src + ' to' + cache_src)
            shutil.copytree(package_src, cache_src)
