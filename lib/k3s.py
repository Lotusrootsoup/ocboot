import os
import hashlib

from lib import consts
from lib.cmd import run_cmd
from lib.ssh import StderrException

def GET_AIRGAP_DIR():
    default_dir = os.path.join(os.getcwd(), "airgap_assets")
    if os.environ.get('K3S_AIRGAP_DIR', None):
        return os.environ.get('K3S_AIRGAP_DIR')
    return default_dir


VERSION_V1_34_2_K3S_1 = "v1.34.2+k3s1"

'''
from:

- https://github.com/k3s-io/k3s/releases/download/v1.29.0%2Bk3s1/sha256sum-amd64.txt
- https://github.com/k3s-io/k3s/releases/download/v1.29.0%2Bk3s1/sha256sum-arm64.txt
'''
SHA256_CHECK_SUM = {
    VERSION_V1_34_2_K3S_1: {
        'k3s': '15811d34187e03fe29d0e46108c42cc33e62cec1b3d9d80f50944536ebcad40a',
        'k3s-airgap-images-amd64.tar.zst': '24359781bd775f513691e98031853d79eac53e265f7d72d1e7325df4f3b18eb0',
        'k3s-arm64': '2e1db0e54a8b0d0ab8a264a119c9c617561f9290e7bb2722d795f8bc91b24cf8',
        'k3s-airgap-images-arm64.tar.zst': '41b34aab92bc5166135dc73217ead65766688fd3543166ce32ffff7e101bef46'
    }
}


def cal_file_sha256(filename):
    sha256_hash = hashlib.sha256()
    with open(filename,"rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def download_asset(dest_dir, k3s_version, asset_url):
    asset_name = os.path.basename(asset_url)
    target_path = os.path.join(dest_dir, asset_name)
    expect_checksum = SHA256_CHECK_SUM[k3s_version][asset_name]
    if os.path.exists(target_path):
        exists_checksum = cal_file_sha256(target_path)
        if exists_checksum == expect_checksum:
            print(f"{target_path} already exists, skip download.")
            return
        else:
            print(f"{target_path}'s sha256 checksum {exists_checksum} != {expect_checksum}, redownload it.")
    run_cmd(f'curl -L {asset_url} > {target_path}', no_strip=True, realtime_output=True)


NO_SUCH_FILE_OR_DIR_ERR = [
    'No such file or directory',
    '没有那个文件或目录',
]


def is_using_k3s(ssh_client=None, use_sudo=False):
    if ssh_client is None:
        if os.environ.get(consts.ENV_K8S_V115) == consts.ENV_VAL_TRUE:
            return False
        return True
    else:
        try:
            kubelet_config = '/etc/kubernetes/kubelet.conf'
            ret = ssh_client.exec_command(f'ls -alh {kubelet_config}', use_sudo)
            if kubelet_config in ret:
                return False
            return True
        except StderrException as e:
            for err in NO_SUCH_FILE_OR_DIR_ERR:
                if err in str(e):
                    return True
            raise e
        except Exception as e:
            raise e


def init_airgap_assets(dest_dir, k3s_version):
    # usage: K3S_URL_PREFIX=http://LOCAL_k3s_host_url
    # in order to speed up testing.
    if not is_using_k3s():
        return

    K3S_URL_PREFIX = os.environ.get('K3S_URL_PREFIX', 'https://github.com/k3s-io/k3s/releases/download/v1.34.2%2Bk3s1')

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    download_asset(dest_dir, k3s_version, f'{K3S_URL_PREFIX}/k3s')
    download_asset(dest_dir, k3s_version, f'{K3S_URL_PREFIX}/k3s-arm64')
    download_asset(dest_dir, k3s_version, f'{K3S_URL_PREFIX}/k3s-airgap-images-arm64.tar.zst')
    download_asset(dest_dir, k3s_version, f'{K3S_URL_PREFIX}/k3s-airgap-images-amd64.tar.zst')

