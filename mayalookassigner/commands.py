from collections import defaultdict
from copy import deepcopy
import json
import logging
import os

import maya.cmds as cmds

import colorbleed.maya.lib as cblib
from avalon import io, api


log = logging.getLogger(__name__)


def get_workfolder():
    return os.path.dirname(cmds.file(query=True, sceneName=True))


def get_selected_assets():
    """Get information from current selection"""

    # TODO: Investigate how we can make `long` argument work

    items = []
    selection = cmds.ls(selection=True)

    containers = get_containers(selection)
    if not containers:
        hierarchy = cmds.listRelatives(selection, allDescendents=True) or []
        containers = get_containers(hierarchy)
        if not containers:
            log.info("No items selected with loaded content")
            return items

    for container, content in containers.iteritems():
        # Ensure we have all
        # Create an item for the tool
        item = create_item_from_container(container, content)
        if not item:
            continue

        items.append(item)

    return items


def get_all_assets():
    """Get all assets from the scene

    Returns:
        list
    """

    host = api.registered_host()

    items = []
    for container in host.ls():
        # We are not interested in looks but assets!
        if container["loader"] == "LookLoader":
            continue
        # Gather all information
        container_name = container["objectName"]
        content = cmds.sets(container_name, query=True)
        item = create_item_from_container(container_name, content)
        if not item:
            continue

        items.append(item)

    return items


def get_containers(nodes):
    """Get containers for the nodes

    Args:
        nodes (list): collect of strings, e.g: selected nodes

    Return:
        dict
    """

    host = api.registered_host()
    results = {}
    nodes = set(nodes)
    for container in host.ls():
        container_object = container['objectName']
        members = set(cmds.sets(container_object, query=True) or [])
        if nodes.intersection(members):
            results[container_object] = list(members)

    return results


def get_asset_id_item(item):

    if cmds.objectType(item) == "objectSet":
        content = cmds.sets(item, query=True)
        shapes = cmds.ls(content, long=True, type="shape")
        assert len(shapes) != 0, "Container has no shapes, this is an error"
        item = shapes[0]

    # Take the first shape, assuming all shapes in the container are from
    # the same asset
    cb_id = cblib.get_id(item)
    if not cb_id:
        return

    asset_id = cb_id.rsplit(":")[0]

    return asset_id


def create_asset_id_hash(nodes):
    """Create a hash based on cbId attribute value
    Args:
        nodes (list): a list of nodes

    Returns:
        dict
    """
    node_id_hash = defaultdict(list)
    for node in nodes:
        value = cblib.get_id(node)
        if value is None:
            continue

        asset_id = value.split(":")[0]
        node_id_hash[asset_id].append(node)

    return node_id_hash


def create_item_from_container(objectname, content):
    """Create an item for the view based the container and content of it

    It fetches the look document based on the asset ID found in the content.
    The item will contain all important information for the tool to work.

    Args:
        objectname(str): name of the objectSet (container)
        content (list): list of items which are in the
    """

    id_hash = create_asset_id_hash(content)
    topnode = cblib.get_container_transforms({"objectName": objectname},
                                             members=content,
                                             root=True)

    try:
        _id = id_hash.keys()[0]
    except IndexError:
        return {}

    asset = io.find_one({"_id": io.ObjectId(_id)}, projection={"name": True})
    looks = fetch_looks([_id])

    return {"asset": asset,
            "objectName": topnode,
            "looks": looks,
            "_id": _id}


def fetch_looks(asset_ids):
    """Get all looks based on the asset id from the cbId attributes

    Use the given asset ID from the attribute which matches an ID from the
    database to use

    Args:
        asset_ids (list): list of unique asset IDs

    Returns:
        looks (list): looks per asset {asset_name : [look_data, look_data]}
    """

    publish_looks = list()
    for asset_id in asset_ids:
        # Get asset name for sorting
        object_id = io.ObjectId(asset_id)

        # Verify if asset ID is correct
        asset = io.find_one({"_id": object_id}, projection={"name": True})
        if not asset:
            raise ValueError("Could not find asset with objectId "
                             "`{}`".format(asset_id))

        # Get all data
        for subset in cblib.list_looks(object_id):
            version = io.find_one({"type": "version", "parent": subset["_id"]},
                                   projection={"name": True, "parent": True},
                                   sort=[("name", -1)])

            publish_looks.append({"asset": asset["name"],
                                  "subset": subset["name"],
                                  "version": version})

    return publish_looks


def process_queued_item(entry):
    """
    Build the correct assignment for the selected asset
    Args:
        entry (dict):

    Returns:

    """

    asset_name = entry["asset"]
    version_id = entry["document"]["_id"]

    # Get the container
    # Check if item is in a container
    container_lookup = get_containers(asset_name)
    if not container_lookup:
        node_name = asset_name.split("|")[-1]
        container_lookup = get_containers([node_name])

    containers = container_lookup.keys()
    assert len(containers) == 1, ("Node is found in no or multiple containers,"
                                  " this is a bug")

    # Get the content of the container
    container = containers[0]
    nodes = cmds.ls(cmds.sets(container, query=True), long=True)

    cblib.assign_look_by_version(nodes, version_id)


def get_asset_data(objectId):

    document = io.find_one({"_id": io.ObjectId(objectId)})
    document_type = document["type"]
    if document_type == "representation":
        version, subset, asset, _ = io.parenthood(document)
    elif document_type == "asset":
        asset = document
    else:
        print("Could not fetch enough data")
        return

    return asset


def create_queue_out_data(queue_items):
    """Create a json friendly data block"""

    items = []
    for item in queue_items:
        # Ensure the io.ObjectId object is a string
        new_item = deepcopy(item)
        new_item["document"]["_id"] = str(item["document"]["_id"])
        new_item["document"]["parent"] = str(item["document"]["parent"])
        items.append(new_item)

    return items


def create_queue_in_data(queue_items):
    """Create a database friendly data block for the tool"""
    items = []
    for item in queue_items:
        new_item = deepcopy(item)
        document = item["document"]
        new_item["document"]["_id"] = io.ObjectId(document["_id"])
        new_item["document"]["parent"] = io.ObjectId(document["parent"])
        items.append(new_item)

    return items


def save_to_json(filepath, items):
    """Store data in a json file"""

    log.info("Writing queue file ...")
    with open(filepath, "w") as fp:
        json.dump(items, fp, ensure_ascii=False)
    log.info("Successfully written file")


def remove_unused_looks():
    """Removes all loaded looks for which none of the shaders are used.

    This will cleanup all loaded "LookLoader" containers that are unused in
    the current scene.

    """

    host = api.registered_host()

    unused = list()
    for container in host.ls():
        if container['loader'] == "LookLoader":
            members = cmds.sets(container['objectName'], query=True)
            look_sets = cmds.ls(members, type="objectSet")
            for look_set in look_sets:
                # If the set is used than we consider this look *in use*
                if cmds.sets(look_set, query=True):
                    break
            else:
                unused.append(container)

    for container in unused:
        log.warning("Removing unused look container: %s",
                    container['objectName'])
        api.remove(container)
