# Copyright (c) 2018, Oracle and/or its affiliates.
# This software is made available to you under the terms of the GPL 3.0 license or the Apache 2.0 license.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# Apache License v2.0
# See LICENSE.TXT for details.

import pytest
from nose.plugins.skip import SkipTest
import logging
from ansible.modules.cloud.oracle import oci_database_facts
from ansible.module_utils.oracle import oci_utils


try:
    import oci
    from oci.database.models import Database
    from oci.exceptions import ServiceError
except ImportError:
    raise SkipTest(
        "test_oci_database_facts.py requires `oci` module")


class FakeModule(object):
    def __init__(self, **kwargs):
        self.params = kwargs

    def fail_json(self, *args, **kwargs):
        self.exit_args = args
        self.exit_kwargs = kwargs
        raise Exception(kwargs['msg'])

    def exit_json(self, *args, **kwargs):
        self.exit_args = args
        self.exit_kwargs = kwargs


@pytest.fixture()
def db_client(mocker):
    mock_db_client = mocker.patch(
        'oci.database.database_client.DatabaseClient')
    return mock_db_client.return_value


@pytest.fixture()
def list_all_resources_patch(mocker):
    return mocker.patch.object(oci_utils, 'list_all_resources')


def setUpModule():
    logging.basicConfig(filename='/tmp/oci_ansible_module.log',
                        filemode='a', level=logging.INFO)
    oci_database_facts.set_logger(logging)


def test_list_databases_list_all(db_client, list_all_resources_patch):
    module = get_module(dict(
        {'compartment_id': 'ocid1.compartment.aaaa', 'db_home_id': 'ocid1.dbhome.aaaa'}))
    list_all_resources_patch.return_value = get_databases()
    result = oci_database_facts.list_databases(db_client, module)
    assert len(result['databases']) is 2


def test_list_databases_list_specific(db_client):
    module = get_module(dict({'database_id': 'ocid1.database.aaaa'}))
    db_client.get_database.return_value = get_response(
        200, None, get_database(), None)
    result = oci_database_facts.list_databases(db_client, module)
    assert result['databases'][0]['db_name'] is 'ansible_database'


def test_list_databases_service_error(db_client):
    error_message = 'Internal Server Error'
    module = get_module(dict({'database_id': 'ocid1.dbsystem.aaaa'}))
    db_client.get_database.side_effect = ServiceError(
        499, 'InternalServerError', dict(), error_message)
    try:
        oci_database_facts.list_databases(db_client, module)
    except Exception as ex:
        assert error_message in ex.args[0]


def get_databases():
    databases = []
    database1 = Database()
    database1.display_name = 'ansible_database1'
    database2 = Database()
    database2.display_name = 'ansible_database2'
    databases.append(database1)
    databases.append(database2)
    return databases


def get_database():
    database = Database()
    database.db_name = 'ansible_database'
    return database


def get_response(status, header, data, request):
    return oci.Response(status, header, data, request)


def get_module(additional_properties):
    params = dict()
    params.update(additional_properties)
    module = FakeModule(**params)
    return module
