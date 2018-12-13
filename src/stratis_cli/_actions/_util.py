# Copyright 2016 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Shared utilities.
"""

from functools import wraps

from .._errors import StratisCliStratisdVersionError

from ._connection import get_object

from ._constants import TOP_OBJECT

from ._data import Manager
from ._data import MOPool
from ._data import MAXIMUM_STRATISD_VERSION
from ._data import REQUIRED_STRATISD_VERSION
from ._data import pools


def get_objects(namespace, pool_name_key, managed_objects, search_function,
                constructor):
    """
    Get objects specified by namespace and designated pool_name_key.
    If no pool name key is specified in the namespace, get objects for all
    pools. Returns objects of interest and also a map from pool object path
    to name for all the pools which have objects in the returned list of
    objects.

    :param Namesapce namespace: the parser namespace
    :param str pool_name_key: the key in the namespace for the pool name
    :param dict managed_objects: the result of a GetManagedObjects call
    :param search_function: function that finds objects of a given type
    :type search_function: dict -> (dict -> list of str * dict)
    :param constructor: function to wrap dict info about a given object

    :returns: objects of interest and a map from pool object path to name
    :rtype: list * dict
    """
    pool_name = getattr(namespace, pool_name_key, None)
    if pool_name is not None:
        (parent_pool_object_path, _) = next(
            pools(props={
                'Name': pool_name
            }).require_unique_match(True).search(managed_objects))

        properties = {"Pool": parent_pool_object_path}
        path_to_name = {parent_pool_object_path: namespace.pool_name}
    else:
        properties = {}
        path_to_name = dict((path, MOPool(info).Name())
                            for path, info in pools().search(managed_objects))

    objects = [
        constructor(info) for _, info in search_function(props=properties, )
        .search(managed_objects)
    ]

    return (objects, path_to_name)


def _verify_stratisd_version():
    """
    Check that the version of stratisd that is running is compatible with
    this version of the CLI. Note that standard packaging should enforce this,
    but users could be running in non-standard ways.

    :returns: the proxy object for TOP_OBJECT
    """
    proxy = get_object(TOP_OBJECT)
    version = Manager.Properties.Version.Get(proxy)
    version = tuple([int(x) for x in version.split(".")])
    if version < REQUIRED_STRATISD_VERSION or version > MAXIMUM_STRATISD_VERSION:
        raise StratisCliStratisdVersionError(
            version, REQUIRED_STRATISD_VERSION, MAXIMUM_STRATISD_VERSION)
    return proxy


def verify_stratisd_version_decorator(orig_func):
    """
    Decorator for stratis methods that call stratisd.

    :param orig_func: the original function
    :type orig_func: (Namespace * object path) -> None
    """

    @wraps(orig_func)
    def the_func(namespace):
        """
        Function that verifies stratisd version is correct before doing
        its principle business.
        """
        orig_func(namespace, _verify_stratisd_version())

    return the_func
