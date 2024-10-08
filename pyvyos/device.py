from typing import Optional, Union, List
import requests
import json
from dataclasses import dataclass

@dataclass
class ApiResponse:
    """
    Represents an API response.

    Attributes:
        status (int): The HTTP status code of the response.
        request (dict): The request payload sent to the API.
        result (dict): The data result of the API response.
        error (str): Any error message in case of a failed response.
    """
    status: int
    request: dict
    result: dict
    error: str

class VyDevice:
    """
    Represents a device for interacting with the VyOS API.

    Args:
        hostname (str): The hostname or IP address of the VyOS device.
        apikey (str): The API key for authentication.
        protocol (str, optional): The protocol to use (default is 'https').
        port (int, optional): The port to use (default is 443).
        verify (bool, optional): Whether to verify SSL certificates (default is True).
        timeout (int, optional): The request timeout in seconds (default is 10).

    Attributes:
        hostname (str): The hostname or IP address of the VyOS device.
        apikey (str): The API key for authentication.
        protocol (str): The protocol used for communication.
        port (int): The port used for communication.
        verify (bool): Whether SSL certificate verification is enabled.
        timeout (int): The request timeout in seconds.

    Methods:
        _get_url(command): Get the full URL for a given API command.
        _get_payload(op, path=[], file=None, url=None, name=None): Generate the API request payload.
        _api_request(command, op, path=[], method='POST', file=None, url=None, name=None): Make an API request.
        retrieve_show_config(path=[]): Retrieve and show the device configuration.
        retrieve_return_values(path=[]): Retrieve and return specific configuration values.
        retrieve_exists(path=[]): Check for the existence of a specific configuration element.
        reset(path=[]): Reset a specific configuration element.
        image_add(url=None, file=None, path=[]): Add an image from a URL or file.
        image_delete(name, url=None, file=None, path=[]): Delete a specific image.
        show(path=[]): Show configuration information.
        generate(path=[]): Generate configuration based on specified path.
        configure_set(path=[]): Sets configuration based on the specified path. This method is versatile, accepting 
        either a single configuration path or a list of configuration paths. This flexibility 
        allows for setting both individual and multiple configurations in a single operation.
        configure_delete(path=[]): Delete configuration based on specified path.
        config_file_save(file=None): Save the configuration to a file.
        config_file_load(file=None): Load the configuration from a file.
        reboot(path=["now"]): Reboot the device.
        poweroff(path=["now"]): Power off the device.
    """

    def __init__(self, hostname, apikey, protocol='https', port=443, verify=True, timeout=10):
        """
        Initializes a VyDevice instance.

        Args:
            hostname (str): The hostname or IP address of the VyOS device.
            apikey (str): The API key for authentication.
            protocol (str, optional): The protocol to use (default is 'https').
            port (int, optional): The port to use (default is 443).
            verify (bool, optional): Whether to verify SSL certificates (default is True).
            timeout (int, optional): The request timeout in seconds (default is 10).
        """
        self.hostname = hostname
        self.apikey = apikey
        self.protocol = protocol
        self.port = port
        self.verify = verify
        self.timeout = timeout

    def _get_url(self, command):
        """
        Get the full URL for a specific API command.

        Args:
            command (str): The API command to construct the URL for.

        Returns:
            str: The full URL for the API command.
        """
        return f"{self.protocol}://{self.hostname}:{self.port}/{command}"

    def _get_payload(self, op, path=[], file=None, url=None, name=None):
        """
        Generate the payload for an API request.

        Args:
            op (str): The operation to perform in the API request.
            path (list, optional): The path elements for the API request (default is an empty list).
            file (str, optional): The file to include in the request (default is None).
            url (str, optional): The URL to include in the request (default is None).
            name (str, optional): The name to include in the request (default is None).

        Returns:
            dict: The payload for the API request.
        """
        if not path:
            data = {
                'op': op,
                'path': path
            }

            if file is not None:
                data['file'] = file
                
            if url is not None:
                data['url'] = url
            
            if name is not None:
                data['name'] = name
                
            payload = {
                'data': json.dumps(data),
                'key': self.apikey
            }

            return payload
        elif isinstance(path, list) and len(path) == 1:
            # If path is a list and contains only one element, use it directly
            data = {'op': op, 'path': path[0]}
        else:
            data = []
            current_command = {'op': op, 'path': []}

            for p in path:
                if isinstance(p, list):
                    # If the current item is a list, merge it into the current command
                    if current_command['path']:
                        data.append(current_command)
                    current_command = {'op': op, 'path': p}
                else:
                    # Otherwise, add the item to the current command's path
                    current_command['path'].append(p)

            # Add the last command to data
            if current_command['path']:
                data.append(current_command)

        payload = {
            'data': json.dumps(data),
            'key': self.apikey
        }

        if file is not None:
            data['file'] = file

        if url is not None:
            payload['url'] = url

        if name is not None:
            data['name'] = name

        return payload

    def _api_request(self, command, op, path=[], file=None, url=None, name=None) -> ApiResponse:
        """
        Make an API request.

        Args:
            command (str): The API command to execute.
            op (str): The operation to perform in the API request.
            path (list, optional): The path elements for the API request (default is an empty list).
            method (str, optional): The HTTP method to use for the request (default is 'POST').
            file (str, optional): The file to include in the request (default is None).
            url (str, optional): The URL to include in the request (default is None).
            name (str, optional): The name to include in the request (default is None).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        url = self._get_url(command)
        payload = self._get_payload(op, path=path, file=file, url=url, name=name)
        
        headers = {}
        error = False      
        result = {}

        try:
            resp = requests.post(url, verify=self.verify, data=payload, timeout=self.timeout, headers=headers)

            if resp.status_code == 200:
                try:
                    resp_decoded = resp.json()
                    
                    if resp_decoded['success'] == True:
                        result = resp_decoded['data']
                        error = False
                    else:   
                        error = resp_decoded['error']
                   
                except json.JSONDecodeError:
                    error = 'json decode error'
            else:
                error = 'http error'

            status = resp.status_code

        except requests.exceptions.ConnectionError as e:
            error = 'connection error: ' + str(e)
            status = 0
  
        # Removing apikey from payload for security reasons
        del(payload['key'])

        return ApiResponse(status=status, request=payload, result=result, error=error)
 
    def retrieve_show_config(self, path: Optional[List[str]]=[]) -> ApiResponse:
        """
        Retrieve and show the device configuration.

        Args:
            path (list, optional): The path elements for the configuration retrieval (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="retrieve", op='showConfig', path=path)

    def retrieve_return_values(self, path: Optional[List[str]]=[]) -> ApiResponse:
        """
        Retrieve and return specific configuration values.

        Args:
            path (list, optional): The path elements for the configuration retrieval (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="retrieve", op='returnValues', path=path)

    def retrieve_exists(self, path: Optional[List[str]]=[]) -> ApiResponse:
        """
        Check for the existence of a specific configuration element.

        Args:
            path (list, optional): The path elements for the configuration retrieval (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="retrieve", op='exists', path=path)

    def reset(self, path: Optional[List[str]]=[]) -> ApiResponse:
        """
        Reset a specific configuration element.

        Args:
            path (list, optional): The path elements for the configuration reset (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="reset", op='reset', path=path)

    def image_add(self, url=None) -> ApiResponse:
        """
        Add an image from a URL or file.

        Args:
            url (str, optional): The URL of the image to add (default is None).
            file (str, optional): The path to the local image file to add (default is None).
            path (list, optional): The path elements for the image addition (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="image", op='add', url=url)

    def image_delete(self, name) -> ApiResponse:
        """
        Delete a specific image.

        Args:
            name (str): The name of the image to delete.
            url (str, optional): The URL of the image to delete (default is None).
            file (str, optional): The path to the local image file to delete (default is None).
            path (list, optional): The path elements for the image deletion (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="image", op='delete', name=name)

    def show(self, path: Optional[List[str]]=[]) -> ApiResponse:
        """
        Show configuration information.

        Args:
            path (list, optional): The path elements for the configuration display (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="show", op='show', path=path)

    def generate(self, path: Optional[List[str]]=[]) -> ApiResponse:
        """
        Generate configuration based on the given path.

        Args:
            path (list, optional): The path elements for configuration generation (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="generate", op='generate', path=path)

    def configure_set(self, path: Optional[Union[List[str], List[List[str]]]]=[]) -> ApiResponse:
        """
        Set configuration based on the given path.

        Args:
            path (list, optional): The path elements for configuration setting (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="configure", op='set', path=path)

    def configure_delete(self, path: Optional[Union[List[str], List[List[str]]]]=[]) -> ApiResponse:
        """
        Delete configuration based on the given path.

        Args:
            path (list, optional): The path elements for configuration deletion (default is an empty list).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="configure", op='delete', path=path)

    def config_file_save(self, file=None) -> ApiResponse:
        """
        Save the configuration to a file.

        Args:
            file (str, optional): The path to the file where the configuration will be saved (default is None).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="config-file", op='save', file=file)

    def config_file_load(self, file=None) -> ApiResponse:
        """
        Load the configuration from a file.

        Args:
            file (str, optional): The path to the file from which the configuration will be loaded (default is None).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="config-file", op='load', file=file)

    def reboot(self, path: Optional[List[str]]=["now"]) -> ApiResponse:
        """
        Reboot the device.

        Args:
            path (list, optional): The path elements for the reboot operation (default is ["now"]).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="reboot", op='reboot', path=path)
    
    def poweroff(self, path: Optional[List[str]]=["now"]) -> ApiResponse:
        """
        Power off the device.

        Args:
            path (list, optional): The path elements for the power off operation (default is ["now"]).

        Returns:
            ApiResponse: An ApiResponse object representing the API response.
        """
        return self._api_request(command="poweroff", op='poweroff', path=path)
