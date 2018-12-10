# Copyright 2018 QuantaStor
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


import mock
import sys

from cinder import context
from cinder.objects import volume as obj_volume
from cinder import test
from cinder.tests.unit import fake_constants as fake
from cinder.volume.drivers import quantastor

CLIENT = 'cinder.volume.drivers.quantastor.QuantaStorDriver'
URLLIB2 = 'cinder.volume.drivers.quantastor_api.requests'
DRIVER_VERSION = '4.0.1'
FAKE_GET_VOL_INFO_RESPONSE = {'name': 'testvolume',
                              'clone': False,
                              'target_name': 'iqn.test',
                              'online': True,
                              'agent_type': 'openstack'}
FAKE_POSITIVE_NETCONFIG_RESPONSE = {
    'role': 'active',
    'subnet_list': [{'network': '172.18.212.0',
                     'discovery_ip': '172.18.108.21',
                     'type': 'data',
                     'allow_iscsi': True,
                     'label': 'data1',
                     'allow_group': True,
                     'vlan_id': 0}],
    'array_list': [{'nic_list': [{'subnet_label': 'data1',
                                  'tagged': False,
                                  'data_ip': '172.18.212.82',
                                  'name': 'eth3'}]}],
    'name': 'test-array'}

FAKE_POSITIVE_LOGIN_RESPONSE_1 = '2c20aad78a220ed1dae21dcd6f9446f5'

FAKE_GENERIC_POSITIVE_RESPONSE = ""

FAKE_LOGIN_POST_RESPONSE = {
    'data': {'session_token': FAKE_POSITIVE_LOGIN_RESPONSE_1}}
FAKE_TYPE_ID = fake.VOLUME_TYPE_ID

FAKE_IGROUP_LIST_RESPONSE = [
    {'iscsi_initiators': [{'iqn': 'test-initiator1'}],
     'name': 'test-igrp1'},
    {'iscsi_initiators': [{'iqn': 'test-initiator2'}],
     'name': 'test-igrp2'}]

FAKE_POSITIVE_GROUP_INFO_RESPONSE = {
    'version_current': '3.0.0.0',
    'group_target_enabled': False,
    'name': 'group',
    'usage_valid': True,
    'usable_capacity_bytes': 8016883089408,
    'compressed_vol_usage_bytes': 2938311843,
    'compressed_snap_usage_bytes': 36189,
    'unused_reserve_bytes': 0}

FAKE_CREATE_VOLUME_POSITIVE_RESPONSE = {
    'clone': False,
    'name': "testvolume"}

FAKE_EXTEND_VOLUME_PARAMS = {'data': {'size': 5120,
                                      'reserve': 0,
                                      'warn_level': 80,
                                      'limit': 100,
                                      'snap_limit': sys.maxsize}}


def create_configuration(username, password, ip_address,
                         pool_id):
    """configuration"""
    configuration = mock.Mock()
    configuration.qs_user = username
    configuration.qs_password = password
    configuration.qs_ip = ip_address
    configuration.qs_pool_id = pool_id
    return configuration


class QuantaStorDriverTestCase(test.TestCase):
    """setup and decorator"""
    def setUp(self):
        super(QuantaStorDriverTestCase, self).setUp()
        self.mock_client_service = None
        self.mock_client_class = None
        self.driver = None

    @staticmethod
    def client_mock_decorator(configuration):
        def client_mock_wrapper(func):
            def inner_client_mock(
                    self, mock_client_class, mock_urllib2):
                self.mock_client_class = mock_client_class
                self.mock_client_service = mock.MagicMock(name='Client')
                self.mock_client_class.return_value = self.mock_client_service
                self.driver = quantastor.QuantaStorDriver(
                    configuration=configuration)
                mock_login_response = mock_urllib2.post.return_value
                mock_login_response = mock.MagicMock()
                mock_login_response.status_code.return_value = 'OK'
                mock_login_response.json.return_value = (
                    FAKE_LOGIN_POST_RESPONSE)
                self.driver.do_setup(context.get_admin_context())
            return inner_client_mock
        return client_mock_wrapper


class QuantaStorDriverUnitTests(QuantaStorDriverTestCase):
    """unit test cases"""
    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    def test_create_snapshot(self):
        """testing create snapshot"""
        self.mock_client_service.snap_vol.return_value = (
            FAKE_GENERIC_POSITIVE_RESPONSE)
        self.driver.create_snapshot(
            {'volume_name': 'testvolume',
             'name': 'testvolume-snap1',
             'display_name': ''})
        self.mock_client_service.snap_vol.assert_called_once_with(
            {'volume_name': 'testvolume',
             'name': 'testvolume-snap1',
             'display_name': ''})

    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    def test_create_volume(self):
        """testing create volume"""
        self.mock_client_service.get_vol_info.return_value = (
            FAKE_GET_VOL_INFO_RESPONSE)
        self.mock_client_service.get_netconfig.return_value = (
            FAKE_POSITIVE_NETCONFIG_RESPONSE)
        self.assertEqual({
            'provider_location': '172.18.108.21:3260 iqn.test',
            'provider_auth': None},
            self.driver.create_volume({'name': 'testvolume',
                                       'size': 1,
                                       'volume_type_id': None,
                                       'display_name': '',
                                       'display_description': ''}))

        self.mock_client_service.create_vol.assert_called_once_with(
            {'name': 'testvolume',
             'size': 1,
             'volume_type_id': None,
             'display_name': '',
             'display_description': ''},
            'default', False, 'iSCSI', False)

    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    @mock.patch.object(obj_volume.VolumeList, 'get_all_by_host')
    def test_create_cloned_volume(self, mock_random, mock_volume_list):
        """testing create cloned volume"""
        mock_random.sample.return_value = fake.VOLUME_ID
        mock_volume_list.return_value = []
        self.mock_client_service.snap_vol.return_value = (
            FAKE_GENERIC_POSITIVE_RESPONSE)
        self.mock_client_service.clone_vol.return_value = (
            FAKE_GENERIC_POSITIVE_RESPONSE)
        self.mock_client_service.get_vol_info.return_value = (
            FAKE_GET_VOL_INFO_RESPONSE)
        self.mock_client_service.get_netconfig.return_value = (
            FAKE_POSITIVE_NETCONFIG_RESPONSE)

        volume = obj_volume.Volume(context.get_admin_context(),
                                   id=fake.VOLUME_ID,
                                   size=5.0,
                                   _name_id=None,
                                   display_name='',
                                   volume_type_id=FAKE_TYPE_ID)
        src_volume = obj_volume.Volume(context.get_admin_context(),
                                       id=fake.VOLUME2_ID,
                                       _name_id=None,
                                       size=5.0)
        self.assertEqual({
            'provider_location': '172.18.108.21:3260 iqn.test',
            'provider_auth': None},
            self.driver.create_cloned_volume(volume, src_volume))

        expected_calls = [mock.call.snap_vol(
            {'volume_name': "volume-" + fake.VOLUME2_ID,
             'name': 'openstack-clone-volume-' + fake.VOLUME_ID + "-" +
                     fake.VOLUME_ID,
             'volume_size': src_volume['size'],
             'display_name': volume['display_name'],
             'display_description': ''}),
            mock.call.clone_vol(volume,
                                {'volume_name': "volume-" + fake.VOLUME2_ID,
                                 'name': 'openstack-clone-volume-' +
                                         fake.VOLUME_ID + "-" +
                                         fake.VOLUME_ID,
                                 'volume_size': src_volume['size'],
                                 'display_name': volume['display_name'],
                                 'display_description': ''},
                                True, False, 'iSCSI', 'default')]

        self.mock_client_service.assert_has_calls(expected_calls)

    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    def test_volume_from_snapshot(self):
        """testing create volume from snapshot"""
        self.mock_client_service.clone_vol.return_value = (
            FAKE_GENERIC_POSITIVE_RESPONSE)
        self.mock_client_service.get_vol_info.return_value = (
            FAKE_GET_VOL_INFO_RESPONSE)
        self.mock_client_service.get_netconfig.return_value = (
            FAKE_POSITIVE_NETCONFIG_RESPONSE)
        self.assertEqual({
            'provider_location': '172.18.108.21:3260 iqn.test',
            'provider_auth': None},
            self.driver.create_volume_from_snapshot(
                {'name': 'clone-testvolume',
                 'size': 2,
                 'volume_type_id': FAKE_TYPE_ID},
                {'volume_name': 'testvolume',
                 'name': 'testvolume-snap1',
                 'volume_size': 1}))
        expected_calls = [
            mock.call.clone_vol(
                {'name': 'clone-testvolume',
                 'volume_type_id': FAKE_TYPE_ID,
                 'size': 2},
                {'volume_name': 'testvolume',
                 'name': 'testvolume-snap1',
                 'volume_size': 1},
                False,
                False,
                'iSCSI',
                'default'),
            mock.call.edit_vol('clone-testvolume',
                               {'data': {'size': 2048,
                                         'snap_limit': sys.maxsize,
                                         'warn_level': 80,
                                         'reserve': 0,
                                         'limit': 100}})]
        self.mock_client_service.assert_has_calls(expected_calls)

    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @mock.patch.object(obj_volume.VolumeList, 'get_all_by_host',
                       mock.Mock(return_value=[]))
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    def test_delete_volume(self):
        """testing delete volume"""
        self.mock_client_service.online_vol.return_value = (
            FAKE_GENERIC_POSITIVE_RESPONSE)
        self.mock_client_service.delete_vol.return_value = (
            FAKE_GENERIC_POSITIVE_RESPONSE)
        self.driver.delete_volume({'name': 'testvolume'})
        expected_calls = [mock.call.online_vol(
            'testvolume', False),
            mock.call.delete_vol('testvolume')]

        self.mock_client_service.assert_has_calls(expected_calls)

    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @mock.patch.object(obj_volume.VolumeList, 'get_all_by_host',
                       mock.Mock(return_value=[]))
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    def test_delete_snapshot(self):
        """testing delete snapshot"""
        self.mock_client_service.online_snap.return_value = (
            FAKE_GENERIC_POSITIVE_RESPONSE)
        self.mock_client_service.delete_snap.return_value = (
            FAKE_GENERIC_POSITIVE_RESPONSE)
        self.driver.delete_snapshot(
            {'volume_name': 'testvolume',
             'name': 'testvolume-snap1'})
        expected_calls = [mock.call.online_snap(
            'testvolume', False, 'testvolume-snap1'),
            mock.call.delete_snap('testvolume',
                                  'testvolume-snap1')]
        self.mock_client_service.assert_has_calls(expected_calls)

    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @mock.patch.object(obj_volume.VolumeList, 'get_all_by_host',
                       mock.Mock(return_value=[]))
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    def test_initialize_connection(self):
        """testing volume attach"""
        self.mock_client_service.get_initiator_grp_list.return_value = (
            FAKE_IGROUP_LIST_RESPONSE)
        expected_res = {
            'driver_volume_type': 'iscsi',
            'data': {
                'volume_id': 12,
                'target_iqn': '13',
                'target_lun': 0,
                'target_portal': '12'}}
        self.assertEqual(
            expected_res,
            self.driver.initialize_connection(
                {'name': 'test-volume',
                 'provider_location': '12 13',
                 'id': 12},
                {'initiator': 'test-initiator1'}))

    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @mock.patch.object(obj_volume.VolumeList, 'get_all_by_host',
                       mock.Mock(return_value=[]))
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    def test_terminate_connection(self):
        """testing dettach volume"""
        self.mock_client_service.get_initiator_grp_list.return_value = (
            FAKE_IGROUP_LIST_RESPONSE)
        self.driver.terminate_connection(
            {'name': 'test-volume',
             'provider_location': '12 13',
             'id': 12},
            {'initiator': 'test-initiator1'})
        expected_calls = [mock.call._get_igroupname_for_initiator(
            'test-initiator1'),
            mock.call.remove_acl({'name': 'test-volume'},
                                 'test-igrp1')]
        self.mock_client_service.assert_has_calls(
            self.mock_client_service.method_calls,
            expected_calls)

    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @mock.patch.object(obj_volume.VolumeList, 'get_all_by_host',
                       mock.Mock(return_value=[]))
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    def test_get_volume_stats(self):
        """testing get volume stats"""
        self.mock_client_service.get_group_info.return_value = (
            FAKE_POSITIVE_GROUP_INFO_RESPONSE)
        expected_res = {'driver_version': DRIVER_VERSION,
                        'vendor_name': 'Quantastor',
                        'volume_backend_name': 'Quantastor',
                        'storage_protocol': 'iSCSI',
                        'pools': [{'pool_name': 'Quantastor',
                                   'total_capacity_gb': 7466.30419921875,
                                   'free_capacity_gb': 7463.567649364471,
                                   'reserved_percentage': 0,
                                   'QoS_support': False}]}
        self.assertEqual(
            expected_res,
            self.driver.get_volume_stats(refresh=True))

    @mock.patch(URLLIB2)
    @mock.patch(CLIENT)
    @mock.patch.object(obj_volume.VolumeList, 'get_all_by_host',
                       mock.Mock(return_value=[]))
    @QuantaStorDriverTestCase.client_mock_decorator(create_configuration(
        'admin', 'password', '192.168.0.101',
        'hofdb0f5c5-834a-1220-96a1-9a5d3f6664a9st'))
    def test_extend_volume(self):
        """testing extend volume"""
        self.mock_client_service.edit_vol.return_value = (
            FAKE_CREATE_VOLUME_POSITIVE_RESPONSE)
        self.driver.extend_volume({'name': 'testvolume'}, 5)

        self.mock_client_service.edit_vol.assert_called_once_with(
            'testvolume', FAKE_EXTEND_VOLUME_PARAMS)
