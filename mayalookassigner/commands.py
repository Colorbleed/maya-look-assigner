import logging
from collections import defaultdict

import maya.cmds as cmds

import colorbleed.maya.lib as lib
from avalon import io


log = logging.getLogger(__name__)


def selection():
    """Get scene selection or list all nodes"""
    nodes = cmds.ls(selection=True, dag=True, long=True)
    if not nodes:
        log.info("No selection found, listing all nodes")
        nodes = cmds.ls(dag=True, long=True)

    return nodes


def create_asset_id_hash(nodes):
    """Create a hash based on cbId attribute value
    Args:
        nodes (list): a list of nodes

    Returns:
        dict
    """

    node_id_hash = defaultdict(list)
    for node in nodes:
        try:
            value = cmds.getAttr("%s.cbId" % node)
        except ValueError:
            continue

        asset_id = value.split(":")[0]
        node_id_hash[asset_id].append(node)

    return node_id_hash


def fetch_looks(asset_ids):
    """Get all looks based on the asset id from the cbId attributes

    Use the given asset ID from the attribute which matches an ID from the
    database to use

    Args:
        asset_ids (list): list of unique asset IDs

    Returns:
        looks (list): looks per asset {asset_name : [look_data, look_data]}
    """

    looks = list()
    for asset_id in asset_ids:
        # get asset name for sorting
        object_id = io.ObjectId(asset_id)
        asset_data = io.find_one({"_id": object_id}, projection={"name": True})
        if not asset_data:
            raise ValueError("Could not find asset with objectId "
                             "`{}`".format(asset_id))

        asset_looks = lib.list_looks(object_id)
        looks.extend([look["name"] for look in asset_looks])

    return looks
