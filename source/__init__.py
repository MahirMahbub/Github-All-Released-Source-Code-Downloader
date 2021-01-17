import os
import threading
from typing import Optional

import requests
from github import Github



class GithubReleaseDownloader:

    def __init__(self, user_name: Optional[str] = None, password: Optional[str] = None,
                 access_token: Optional[str] = None):
        self.user_name: str = user_name
        self.password: str = password
        self.access_token: str = access_token


    @staticmethod
    def download_url(url, save_path=os.getcwd(), chunk_size=64):
        r = requests.get(url, stream=True)
        with open(save_path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)


    def _create_new_download_thread(self, url, save_path, chunk_size=64):
        download_thread = threading.Thread(target=self.download_url, args=(url, save_path, chunk_size))
        download_thread.start()
        return download_thread


    def download_releases(self, repository: str,
                          save_path: str = os.getcwd(), thread_number: int = 5):
        if thread_number > 128:
            assert "Number of Thread is too high"
        cred = self._authenticate_to_github(self.access_token, self.password, self.user_name)
        repo = cred.get_repo(repository)
        repo_name = self._get_repository_name(repository)
        releases = repo.get_releases()
        download_links = self._get_release_zipball_urls(releases)
        number_of_release = len(download_links)
        for start_index in range(0, number_of_release, thread_number):
            last_index, thread_list = self._calculate_last_index_for_threading(number_of_release, start_index,
                                                                               thread_number)
            for ref in download_links[start_index:last_index]:
                print("Downloading.....: ", ref)
                version_name = self._get_release_version(ref)
                self._check_and_create_local_repo_dir(repo_name, save_path)
                thread_list.append(
                    self._create_new_download_thread(url=ref,
                                                     save_path=save_path + "\\" + repo_name + "\\" + version_name +
                                                               ".tar.gz",
                                                     chunk_size=320 // number_of_release))
            for thread in thread_list:
                thread.join()


    @staticmethod
    def _check_and_create_local_repo_dir(repo_name, save_path):
        if not os.path.exists(save_path + "\\" + repo_name):
            os.makedirs(save_path + "\\" + repo_name)


    @staticmethod
    def _get_release_version(ref):
        version_name = ref.split("/")[-1]
        return version_name


    @staticmethod
    def _calculate_last_index_for_threading(number_of_release, start_index, thread_number):
        last_index = start_index + thread_number
        if last_index > number_of_release:
            last_index = number_of_release
        thread_list = []
        return last_index, thread_list


    @staticmethod
    def _get_repository_name(repository):
        repo_name = repository.split('/')[-1]
        return repo_name


    @staticmethod
    def _get_release_zipball_urls(releases):
        download_links = []
        for release in releases:
            download_links.append(release.zipball_url)
        return download_links


    @staticmethod
    def _authenticate_to_github(access_token, password, user_name):
        if access_token is None:
            cred = Github(user_name, password)
        else:
            cred = Github(access_token)
        return cred
