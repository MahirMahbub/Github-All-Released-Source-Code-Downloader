import os
import threading
from threading import Thread
from typing import Optional, List

import requests
from github import Github
from github.GitRelease import GitRelease
from github.PaginatedList import PaginatedList
from github.Repository import Repository
from pydantic import HttpUrl
from requests import Response



class GithubReleaseDownloader(object):

    def __init__(self, user_name: Optional[str] = None, password: Optional[str] = None,
                 access_token: Optional[str] = None):
        self._user_name: str = user_name
        self._password: str = password
        self._access_token: str = access_token


    @staticmethod
    def download_url(url: HttpUrl, save_path: Optional[str] = os.getcwd(), chunk_size: Optional[int] = 64):
        r: Response = requests.get(url, stream=True)
        with open(save_path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)


    def _create_new_download_thread(self, url: str, save_path: str, chunk_size: int):
        download_thread: Thread = threading.Thread(target=self.download_url, args=(url, save_path, chunk_size))
        download_thread.start()
        return download_thread


    def download_releases(self, repository: str,
                          save_path: Optional[str] = os.getcwd(), thread_number: Optional[int] = 5):
        if thread_number > 128:
            assert "Number of Thread is too high"
        _cred: Github = self._authenticate_to_github(self._access_token, self._password, self._user_name)
        _repo: Repository = _cred.get_repo(repository)
        _repo_name: str = self._get_repository_name(repository)
        _releases: PaginatedList[GitRelease] = _repo.get_releases()
        _download_links: List[str] = self._get_release_zipball_urls(_releases)
        _number_of_release: int = len(_download_links)
        for start_index in range(0, _number_of_release, thread_number):
            _last_index: int
            _thread_list: List[Thread]
            _last_index, _thread_list = self._calculate_last_index_for_threading(_number_of_release, start_index,
                                                                                 thread_number)
            for ref in _download_links[start_index:_last_index]:
                print("Downloading.....: ", ref)
                _version_name: str = self._get_release_version(ref)
                self._check_and_create_local_repo_dir(_repo_name, save_path)
                _thread_list.append(
                    self._create_new_download_thread(url=ref,
                                                     save_path=save_path + "\\" + _repo_name + "\\" + _version_name +
                                                               ".tar.gz",
                                                     chunk_size=320 // _number_of_release))
            for thread in _thread_list:
                thread.join()


    @staticmethod
    def _check_and_create_local_repo_dir(repo_name: str, save_path: str):
        if not os.path.exists(save_path + "\\" + repo_name):
            os.makedirs(save_path + "\\" + repo_name)


    @staticmethod
    def _get_release_version(ref: str):
        version_name: str = ref.split("/")[-1]
        return version_name


    @staticmethod
    def _calculate_last_index_for_threading(number_of_release: int, start_index: int, thread_number: int):
        last_index: int = start_index + thread_number
        if last_index > number_of_release:
            last_index = number_of_release
        thread_list: List[Thread] = []
        return last_index, thread_list


    @staticmethod
    def _get_repository_name(repository: str):
        repo_name: str = repository.split('/')[-1]
        return repo_name


    @staticmethod
    def _get_release_zipball_urls(releases: PaginatedList[GitRelease]):
        download_links: List[str] = []
        for release in releases:
            download_links.append(release.zipball_url)
        return download_links


    @staticmethod
    def _authenticate_to_github(access_token: str, password: str, user_name: str):
        if access_token is None:
            cred: Github = Github(user_name, password)
        else:
            cred: Github = Github(access_token)
        return cred
