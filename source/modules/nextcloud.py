import os
import logging
import nc_py_api
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(os.environ["LOGLEVEL"])

class nextcloud:

	nc = None,
	nextcloud_url = None
	nc_auth_user = None
	nc_auth_pass = None


	def __init__(self, nextcloud_url, nc_auth_user, nc_auth_pass):
		
		self.nextcloud_url=nextcloud_url
		self.nc_auth_user=nc_auth_user
		self.nc_auth_pass=nc_auth_pass


	async def list_dir(self, path):

		file_list = []

		self.nc = nc_py_api.AsyncNextcloud(nextcloud_url=self.nextcloud_url, nc_auth_user=self.nc_auth_user, nc_auth_pass=self.nc_auth_pass)

		# usual recursive traversing over directories
		for node in await self.nc.files.listdir(path):
			if node.is_dir:
					await self.list_dir(node)
			else:
					logger.info("Found file %s", node.user_path)
					file_list.append(node.user_path)

		logging.debug("Found files:")
		for file in file_list:
				logging.debug(file)
		
		return file_list


	async def get_file_modified_timestamp(self, path):

		self.nc = nc_py_api.AsyncNextcloud(nextcloud_url=self.nextcloud_url, nc_auth_user=self.nc_auth_user, nc_auth_pass=self.nc_auth_pass)

		node = await self.nc.files.by_path(path)

		return node.info.last_modified



	async def download_files(self, list, destination):

		self.nc = nc_py_api.AsyncNextcloud(nextcloud_url=self.nextcloud_url, nc_auth_user=self.nc_auth_user, nc_auth_pass=self.nc_auth_pass)

		if os.path.exists(destination):
			shutil.rmtree(destination)

		for file in list:

			filename = file.rsplit('/')[-1]
			logger.debug("Downloading file %s to %s", filename, destination)
			download_bytes = await self.nc.files.download(file)
			file_meta = await self.nc.files.by_path(file)
			file_last_modified = file_meta.info.last_modified

			if not os.path.exists(destination):
					os.makedirs(destination)

			with open(f"{destination}/{filename}", "wb") as song_file:
				song_file.write(download_bytes)

			os.utime(f"{destination}/{filename}", (file_last_modified.timestamp(), file_last_modified.timestamp()))