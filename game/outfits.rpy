
init -2:
    default persistent.jn_natsuki_auto_outfit_change_enabled = True
    default persistent.jn_custom_outfits_unlocked = False
    default persistent.jn_natsuki_outfit_on_quit = "jn_school_uniform"
    default persistent.jn_outfit_list = {}
    default persistent.jn_wearable_list = {}

init -1 python in jn_outfits:
    from Enum import Enum
    import json
    import os
    import random
    import re
    import store
    import store.jn_affinity as jn_affinity
    import store.jn_utils as jn_utils
    import time

    # Critical file paths
    __CUSTOM_WEARABLES_DIRECTORY = os.path.join(renpy.config.basedir, "custom_wearables/").replace("\\", "/")
    __CUSTOM_OUTFITS_DIRECTORY = os.path.join(renpy.config.basedir, "custom_outfits/").replace("\\", "/")
    __WEARABLE_BASE_PATH = os.path.join(renpy.config.basedir, "game/mod_assets/natsuki/")

    # Ignore the syntax highlighting - "it just works"
    __RESTRICTED_CHARACTERS_REGEX = "((\.)|(\[)|(\])|(\})|(\{)|(,)|(\!))"

    # Lists of all registered outfits/wearables
    __ALL_WEARABLES = {}
    __ALL_OUTFITS = {}

    _PREVIEW_OUTFIT = None
    _LAST_OUTFIT = None

    _SESSION_NEW_UNLOCKS = list()

    _changes_made = False

    # Wearables being registered via JSON must be one of the following types
    WEARABLE_CATEGORIES = [
        "hairstyle",
        "eyewear",
        "accessory",
        "clothes",
        "headgear",
        "necklace",
        "facewear",
        "back"
    ]

    class JNWearable():
        """
        Describes a standalone object that Natsuki can wear.
        """
        def __init__(
            self,
            reference_name,
            display_name,
            unlocked,
            is_jn_wearable
        ):
            """
            Constructor.

            IN:
                - reference_name - The name used to uniquely identify this wearable and refer to it internally
                - display_name - The name displayed to the user
                - unlocked - Whether or not this wearable is selectable to the player on menus
                - is_jn_wearable - Whether or not this wearable is an official JN wearable. Official wearables cannot be deleted/modified.
            """
            self.reference_name = reference_name
            self.display_name = display_name
            self.unlocked = unlocked
            self.is_jn_wearable = is_jn_wearable

        @staticmethod
        def load_all():
            """
            Loads all persisted data for each wearable from the persistent.
            """
            global __ALL_WEARABLES
            for wearable in __ALL_WEARABLES.values():
                wearable.__load()

        @staticmethod
        def save_all():
            """
            Saves all persistable data for each wearable to the persistent.
            """
            global __ALL_WEARABLES
            for wearable in __ALL_WEARABLES.values():
                wearable.__save()

        @staticmethod
        def filter_wearables(
            wearable_list,
            unlocked=None,
            is_jn_wearable=None,
            reference_name=None,
            not_reference_name=None,
            wearable_type=None
        ):
            """
            Returns a filtered list of wearables, given an wearable list and filter criteria.

            IN:
                - wearable_list - the list of JNWearable child wearables to query
                - unlocked - the boolean unlocked state to filter for
                - is_jn_wearable - the boolean is_jn_wearable state to filter for
                - reference_name - list of reference_names the wearable must have
                - not_reference_name - list of reference_names the wearable must not have
                - wearable_type the wearable type to filter for

            OUT:
                - list of JNWearable child wearables matching the search criteria
            """
            return [
                _wearable
                for _wearable in wearable_list
                if _wearable.__filter_wearable(
                    unlocked,
                    is_jn_wearable,
                    reference_name,
                    not_reference_name,
                    wearable_type
                )
            ]

        def as_dict(self):
            """
            Exports a dict representation of this wearable; this is for data we want to persist.

            OUT:
                dictionary representation of the wearable object
            """
            return {
                "unlocked": self.unlocked
            }

        def unlock(self):
            """
            Unlocks this wearable, making it available to the player.
            """
            # Unlock the wearable
            self.unlocked = True
            self.__save()

        def lock(self):
            """
            Locks this wearable, making it unavailable to the player.
            """
            # Unlock the wearable
            self.unlocked = False
            self.__save()

        def __load(self):
            """
            Loads the persisted data for this wearable from the persistent.
            """
            if store.persistent.jn_wearable_list[self.reference_name]:
                self.unlocked = store.persistent.jn_wearable_list[self.reference_name]["unlocked"]

        def __save(self):
            """
            Saves the persistable data for this wearable to the persistent.
            """
            store.persistent.jn_wearable_list[self.reference_name] = self.as_dict()

        def __filter_wearable(
            self,
            unlocked=None,
            is_jn_wearable=None,
            reference_name=None,
            not_reference_name=None,
            wearable_type=None
        ):
            """
            Returns True, if the wearable meets the filter criteria. Otherwise False.

            IN:
                - wearable_list - the list of JNWearable child wearables to query
                - unlocked - the boolean unlocked state to filter for
                - is_jn_wearable - the boolean is_jn_wearable state to filter for
                - reference_name - list of reference_names the wearable must have
                - not_reference_name - list of reference_names the wearable must not have
                - wearable_type the wearable type to filter for

            OUT:
                - True, if the wearable meets the filter criteria. Otherwise False
            """
            if unlocked is not None and self.unlocked != unlocked:
                return False

            elif is_jn_wearable is not None and self.is_jn_wearable != is_jn_wearable:
                return False

            elif reference_name is not None and not self.reference_name in reference_name:
                return False

            elif not_reference_name is not None and self.reference_name in not_reference_name:
                return False

            elif wearable_type is not None and not isinstance(self, wearable_type):
                return False

            return True

    class JNHairstyle(JNWearable):
        """
        Describes a hairstyle for Natsuki; a wearable with additional functionality specific to hairstyles.
        """
        def getFolderName(self):
            return "hair"

    class JNEyewear(JNWearable):
        """
        Describes eyewear for Natsuki; a wearable with additional functionality specific to eyewear.
        """
        def getFolderName(self):
            return "eyewear"

    class JNAccessory(JNWearable):
        """
        Describes an accessory for Natsuki; a wearable with additional functionality specific to accessories.
        """
        def getFolderName(self):
            return "accessory"

    class JNClothes(JNWearable):
        """
        Describes a set of clothes for Natsuki; a wearable with additional functionality specific to clothes.
        """
        def getFolderName(self):
            return "clothes"

    class JNHeadgear(JNWearable):
        """
        Describes some headgear for Natsuki; a wearable with additional functionality specific to headgear.
        """
        def getFolderName(self):
            return "headgear"

    class JNNecklace(JNWearable):
        """
        Describes some headgear for Natsuki; a wearable with additional functionality specific to necklaces.
        """
        def getFolderName(self):
            return "necklace"

    class JNFacewear(JNWearable):
        """
        Describes some facewear for Natsuki; a wearable with additional functionality specific to facewear.
        """
        def getFolderName(self):
            return "facewear"

    class JNBack(JNWearable):
        """
        Describes some back item for Natsuki; a wearable with additional functionality specific to back items.
        """
        def getFolderName(self):
            return "back"

    class JNOutfit():
        """
        Describes a complete outfit for Natsuki to wear; including clothing, hairstyle, etc.
        At minimum, an outfit must consist of clothes and a hairstyle.
        """
        def __init__(
            self,
            reference_name,
            display_name,
            unlocked,
            is_jn_outfit,
            clothes,
            hairstyle,
            accessory=None,
            eyewear=None,
            headgear=None,
            necklace=None,
            facewear=None,
            back=None
        ):
            """
            Constructor.

            IN:
                - reference_name - The name used to uniquely identify this outfit and refer to it internally
                - display_name - The name displayed to the user
                - unlocked - Whether or not this outfit is selectable to the player on menus
                - is_jn_outfit - Whether or not this outfit is an official JN outfit. Official outfits cannot be deleted/modified.
                - clothes - JNClothes associated with this outfit.
                - hairstyle - JNHairstyle associated with this outfit.
                - accessory - JNAccessory associated with this outfit. Optional.
                - eyewear - JNEyewear associated with this outfit. Optional.
                - headgear - JNHeadgear associated with this outfit. Optional.
                - necklace - JNNecklace associated with this outfit. Optional.
                - facewear - JNFacialwear associated with this outfit. Optional.
                - back - JNBack associated with this outfit. Optional.
            """
            # Clothes are required
            if clothes is None:
                raise TypeError("Outfit clothing cannot be None")
                return

            # Hairstyle is required
            if hairstyle is None:
                raise TypeError("Outfit hairstyle cannot be None")
                return

            self.reference_name = reference_name
            self.display_name = display_name
            self.unlocked = unlocked
            self.is_jn_outfit = is_jn_outfit
            self.clothes = clothes
            self.hairstyle = hairstyle
            self.accessory = accessory
            self.eyewear = eyewear
            self.headgear = headgear
            self.necklace = necklace
            self.facewear = facewear
            self.back = back

        @staticmethod
        def load_all():
            """
            Loads all persisted data for each outfit from the persistent.
            """
            global __ALL_OUTFITS
            for outfit in __ALL_OUTFITS.values():
                outfit.__load()

        @staticmethod
        def save_all():
            """
            Saves all persistable data for each outfit to the persistent.
            """
            global __ALL_OUTFITS
            for outfit in __ALL_OUTFITS.values():
                outfit.__save()

        @staticmethod
        def filter_outfits(
            outfit_list,
            unlocked=None,
            is_jn_outfit=None,
            not_reference_name=None,
            has_accessory=None,
            has_eyewear=None,
            has_headgear=None,
            has_necklace=None,
            has_facewear=None,
            has_back=None
        ):
            """
            Returns a filtered list of outfits, given an outfit list and filter criteria.

            IN:
                - outfit_list - the list of JNOutfit outfits to query
                - unlocked - the boolean unlocked state to filter for
                - is_jn_outfit - the boolean is_jn_outfit state to filter for
                - not_reference_name - list of reference_names the outfit must not have
                - has_accessory - the boolean has_accessory state to filter for
                - has_eyewear - the boolean has_eyewear state to filter for
                - has_headgear - the boolean has_headgear state to filter for
                - has_necklace - the boolean has_necklace state to filter for
                - has_facewear - the boolean has_facewear state to filter for
                - has_back - the boolean has_back state to filter for

            OUT:
                - list of JNOutfit outfits matching the search criteria
            """
            return [
                _outfit
                for _outfit in outfit_list
                if _outfit.__filter_outfit(
                    unlocked,
                    is_jn_outfit,
                    not_reference_name,
                    has_accessory,
                    has_eyewear,
                    has_headgear,
                    has_necklace,
                    has_facewear,
                    has_back
                )
            ]

        def as_dict(self):
            """
            Exports a dict representation of this outfit; this is for data we want to persist.

            OUT:
                dictionary representation of the outfit object
            """
            return {
                "unlocked": self.unlocked
            }

        def unlock(self):
            """
            Unlocks this outfit, making it (and all constituent wearables) available to the player.
            """
            # Unlock the outfit
            self.unlocked = True
            self.__save()

            # Unlock outfit components
            if not self.clothes.unlocked:
                self.clothes.unlock()

            if not self.hairstyle.unlocked:
                self.hairstyle.unlock()

            if self.accessory and not self.accessory.unlocked:
                self.accessory.unlock()

            if self.eyewear and not self.eyewear.unlocked:
                self.eyewear.unlock()

            if self.headgear and not self.headgear.unlocked:
                self.headgear.unlock()

            if self.necklace and not self.necklace.unlocked:
                self.necklace.unlock()

            if self.facewear and not self.facewear.unlocked:
                self.facewear.unlock()

            if self.back and not self.back.unlocked:
                self.back.unlock()

        def lock(self):
            """
            Locks this outfit, making it unavailable to the player.
            Any constituent wearables remain unlocked however, as these can be used in custom outfits/other JN outfits.
            """
            self.unlocked = False
            self.__save()

        def to_json_string(self):
            """
            Returns this outfit as a JSON string for export use.
            """
            # Core fields
            outfit_dict = {
                    "reference_name": self.reference_name,
                    "display_name": self.display_name,
                    "unlocked": True, # An outfit a user can create should never be locked by default
                    "clothes": self.clothes.reference_name,
                    "hairstyle": self.hairstyle.reference_name
                }

            # Optional fields
            if self.headgear and isinstance(self.headgear, JNHeadgear):
                outfit_dict["headgear"] = self.headgear.reference_name

            if self.eyewear and isinstance(self.eyewear, JNEyewear):
                outfit_dict["eyewear"] = self.eyewear.reference_name

            if self.accessory and isinstance(self.accessory, JNAccessory):
                outfit_dict["accessory"] = self.accessory.reference_name

            if self.necklace and isinstance(self.necklace, JNNecklace):
                outfit_dict["necklace"] = self.necklace.reference_name

            if self.facewear and isinstance(self.necklace, JNFacewear):
                outfit_dict["facewear"] = self.facewear.reference_name

            if self.back and isinstance(self.back, JNBack):
                outfit_dict["back"] = self.back.reference_name

            return json.dumps(outfit_dict)

        def __load(self):
            """
            Loads the persisted data for this outfit from the persistent, if it exists.
            """
            if store.persistent.jn_outfit_list[self.reference_name]:
                self.unlocked = store.persistent.jn_outfit_list[self.reference_name]["unlocked"]

        def __save(self):
            """
            Saves the persistable data for this outfit to the persistent.
            """
            store.persistent.jn_outfit_list[self.reference_name] = self.as_dict()

        def __delete_save(self):
            """
            Deletes the persistable data for this outfit from the persistent, if it exists.
            """
            if store.persistent.jn_outfit_list[self.reference_name]:
                del store.persistent.jn_outfit_list[self.reference_name]

        def __filter_outfit(
            self,
            unlocked=None,
            is_jn_outfit=None,
            not_reference_name=None,
            has_accessory=None,
            has_eyewear=None,
            has_headgear=None,
            has_necklace=None,
            has_facewear=None,
            has_back=None
        ):
            """
            Returns True, if the outfit meets the filter criteria. Otherwise False.

            IN:
                - unlocked - the boolean unlocked state to filter for
                - is_jn_outfit - the boolean is_jn_outfit state to filter for
                - not_reference_name - list of reference_names the outfit must not have
                - has_accessory - the boolean has_accessory state to filter for
                - has_eyewear - the boolean has_eyewear state to filter for
                - has_headgear - the boolean has_headgear state to filter for
                - has_necklace - the boolean has_necklace state to filter for
                - has_facewear - the boolean has_facewear state to filter for
                - has_back - the boolean has_back state to filter for

            OUT:
                - True, if the outfit meets the filter criteria. Otherwise False
            """
            if unlocked is not None and self.unlocked != unlocked:
                return False

            elif is_jn_outfit is not None and self.is_jn_outfit != is_jn_outfit:
                return False

            elif not_reference_name is not None and self.reference_name in not_reference_name:
                return False

            elif has_accessory is not None and bool(self.has_accessory) != has_accessory:
                return False

            elif has_eyewear is not None and bool(self.has_eyewear) != has_eyewear:
                return False

            elif has_headgear is not None and bool(self.has_headgear) != has_headgear:
                return False

            elif has_necklace is not None and bool(self.has_necklace) != has_necklace:
                return False

            elif has_facewear is not None and bool(self.has_facewear) != has_facewear:
                return False

            elif has_back is not None and bool(self.has_back) != has_back:
                return False

            return True

    def __register_outfit(outfit, player_created=False):
        """
        Registers a new outfit in the list of all outfits, allowing in-game access and persistency.
        If the outfit has no existing corresponding persistent entry, it is saved.

        IN:
            - outfit - the JNOutfit to register.
            - player_created - Boolean flag describing whether this outfit was defined by the current player via the new outfit creation flow
        """
        if outfit.reference_name in __ALL_OUTFITS:
            jn_utils.log("Cannot register outfit name: {0}, as an outfit with that name already exists.".format(outfit.reference_name))

        else:
            if not outfit.accessory:
                outfit.accessory = get_wearable("jn_none")

            if not outfit.eyewear:
                outfit.eyewear = get_wearable("jn_none")

            if not outfit.headgear:
                outfit.headgear = get_wearable("jn_none")

            if not outfit.necklace:
                outfit.necklace = get_wearable("jn_none")

            if not outfit.facewear:
                outfit.facewear = get_wearable("jn_none")

            if not outfit.back:
                outfit.back = get_wearable("jn_none")

            __ALL_OUTFITS[outfit.reference_name] = outfit
            if outfit.reference_name not in store.persistent.jn_outfit_list:
                outfit.__save()

                # If this is the first time adding it to the list, and it isn't JN or created by this player in the session, it's a new unlock
                if not "jn_" in outfit.reference_name and not player_created:
                    _SESSION_NEW_UNLOCKS.append(outfit)

    def __register_wearable(wearable):
        """
        Registers a new wearable in the list of all wearables, allowing in-game access and persistency.
        """
        if wearable.reference_name in __ALL_WEARABLES:
            jn_utils.log("Cannot register wearable name: {0}, as a wearable with that name already exists.".format(wearable.reference_name))

        else:
            __ALL_WEARABLES[wearable.reference_name] = wearable
            if wearable.reference_name not in store.persistent.jn_wearable_list:
                wearable.__save()

                # If this is the first time adding it to the list, and it isn't JN, it's a new unlock
                if not "jn_" in wearable.reference_name:
                    _SESSION_NEW_UNLOCKS.append(wearable)

            else:
                wearable.__load()

    def __delete_outfit(outfit):
        """
        Deletes an outfit from the list of all outfits.
        If the outfit has a corresponding persistent entry, it is deleted.
        """
        outfit.__delete_save()
        del __ALL_OUTFITS[outfit.reference_name]

    def _check_wearable_sprites(wearable):
        """
        Checks sprite paths based on wearable type to ensure all required assets exist.

        IN:
            - wearable - the JNWearable wearable to test

        OUT:
            - True if all required assets for the wearable exist, otherwise False
        """
        WEARABLE_COMMON_PATH = os.path.join(__WEARABLE_BASE_PATH, wearable.getFolderName())

        for pose in store.JNPose:

            # Note that for now, only the clothes are pose-sensitive; all other wearables only need a sitting sprite

            if isinstance(wearable, JNClothes):
                # Clothes have both a sleeves and body portion, so we must check both exist
                sleeves_path = os.path.join(__WEARABLE_BASE_PATH, "sleeves", wearable.reference_name, "{0}.png".format(pose.name))
                clothes_path = os.path.join(__WEARABLE_BASE_PATH, "clothes", wearable.reference_name, "{0}.png".format(pose.name))

                if not jn_utils.getFileExists(sleeves_path) or not jn_utils.getFileExists(clothes_path):
                    jn_utils.log("Missing clothes/sleeves_path sprite(s) for {0}".format(wearable.reference_name))
                    return False

            elif isinstance(wearable, JNHairstyle):
                # Hairstyles have two sprites for a given pose (front/bangs and back), so we must check both exist
                back_path = os.path.join(WEARABLE_COMMON_PATH, wearable.reference_name, "sitting", "back.png")
                bangs_path = os.path.join(WEARABLE_COMMON_PATH, wearable.reference_name, "sitting", "bangs.png")

                if not jn_utils.getFileExists(back_path) or not jn_utils.getFileExists(bangs_path):
                    jn_utils.log("Missing back/bangs sprite(s) for {0}".format(wearable.reference_name))
                    return False

            else:
                # Any other wearable only has one sprite for a given pose
                resource_path = os.path.join(WEARABLE_COMMON_PATH, wearable.reference_name, "sitting.png")

                if not jn_utils.getFileExists(resource_path):
                    jn_utils.log("Missing sprite(s) for {0}: check {1}".format(wearable.reference_name, resource_path))
                    return False

        return True

    def _load_wearable_from_json(json):
        """
        Attempts to load a wearable from a JSON object and register it.

        IN:
            - json - JSON object describing the wearable
        """
        # Sanity check the structure to make sure minimum attributes are specified
        if (
            "reference_name" not in json
            or "display_name" not in json
            or "unlocked" not in json
            or "category" not in json
        ):
            jn_utils.log("Cannot load wearable as one or more key attributes do not exist.")
            return False

        # Sanity check data types
        elif (
            not isinstance(json["reference_name"], basestring)
            or not isinstance(json["display_name"], basestring)
            or not isinstance(json["unlocked"], bool)
            or not isinstance(json["category"], basestring)
            or not json["category"] in WEARABLE_CATEGORIES
        ):
            jn_utils.log("Cannot load wearable {0} as one or more attributes are the wrong data type.".format(json["reference_name"]))
            return False

        # Prevent use of the jn_ namespace
        elif re.search("^jn_.", json["reference_name"].lower()):
            jn_utils.log("Cannot load wearable {0} as the reference name contains a reserved namespace.".format(json["reference_name"]))
            return False

        # Prevent use of Ren'Py interpolation characters
        elif re.search(__RESTRICTED_CHARACTERS_REGEX, json["reference_name"]):
            jn_utils.log("Cannot load wearable {0} as the reference name contains one or more restricted characters.".format(json["reference_name"]))
            return False

        else:
            # Register based on category
            kwargs = {
                "reference_name": json["reference_name"],
                "display_name": json["display_name"],
                "unlocked": json["unlocked"],
                "is_jn_wearable": False
            }

            if json["category"] == "hairstyle":
                wearable = JNHairstyle(**kwargs)

            elif json["category"] == "eyewear":
                wearable = JNEyewear(**kwargs)

            elif json["category"] == "accessory":
                wearable = JNAccessory(**kwargs)

            elif json["category"] == "clothes":
                wearable = JNClothes(**kwargs)

            elif json["category"] == "headgear":
                wearable = JNHeadgear(**kwargs)

            elif json["category"] == "necklace":
                wearable = JNNecklace(**kwargs)

            elif json["category"] == "facewear":
                wearable = JNFacewear(**kwargs)

            elif json["category"] == "back":
                wearable = JNBack(**kwargs)

            # Finally, make sure the resources necessary for this wearable exist
            if not _check_wearable_sprites(wearable):
                jn_utils.log("Cannot load wearable {0} as one or more sprites are missing.".format(wearable.reference_name))
                return False

            __register_wearable(wearable)
            return True

    def _load_outfit_from_json(json):
        """
        Attempts to load an outfit from a JSON object and register it.

        IN:
            - json - JSON object describing the outfit

        OUT: True if load was successful, otherwise False
        """
        # Sanity check the structure to make sure minimum attributes are specified
        if (
            "reference_name" not in json
            or "display_name" not in json
            or "unlocked" not in json
            or "clothes" not in json
            or "hairstyle" not in json
        ):
            jn_utils.log("Cannot load outfit as one or more key attributes do not exist.")
            return False

        # Sanity check data types
        elif (
            not isinstance(json["reference_name"], basestring)
            or not isinstance(json["display_name"], basestring)
            or not isinstance(json["unlocked"], bool)
            or not isinstance(json["clothes"], basestring)
            or not isinstance(json["hairstyle"], basestring)
            or "eyewear" in json and not isinstance(json["eyewear"], basestring)
            or "headgear" in json and not isinstance(json["headgear"], basestring)
            or "necklace" in json and not isinstance(json["necklace"], basestring)
            or "facewear" in json and not isinstance(json["facewear"], basestring)
            or "back" in json and not isinstance(json["back"], basestring)
        ):
            jn_utils.log("Cannot load outfit as one or more attributes are the wrong data type.")
            return False

        # Prevent use of the jn_ namespace
        elif re.search("^jn_.", json["reference_name"].lower()):
            jn_utils.log("Cannot load outfit {0} as the reference name contains a reserved namespace.".format(json["reference_name"]))
            return False

        # Prevent use of Ren'Py interpolation characters
        elif re.search(__RESTRICTED_CHARACTERS_REGEX, json["reference_name"]):
            jn_utils.log("Cannot load outfit {0} as the reference name contains one or more restricted characters.".format(json["reference_name"]))
            return False

        # Sanity check components to make sure they exist as registered wearables
        if not json["clothes"] in __ALL_WEARABLES:
            jn_utils.log("Cannot load outfit {0} as specified clothes do not exist.".format(json["reference_name"]))
            return False

        elif not json["hairstyle"] in __ALL_WEARABLES:
            jn_utils.log("Cannot load outfit {0} as specified hairstyle does not exist.".format(json["reference_name"]))
            return False

        elif "accessory" in json and not json["accessory"] in __ALL_WEARABLES:
            jn_utils.log("Cannot load outfit {0} as specified accessory does not exist.".format(json["reference_name"]))
            return False

        elif "eyewear" in json and not json["eyewear"] in __ALL_WEARABLES:
            jn_utils.log("Cannot load outfit {0} as specified eyewear does not exist.".format(json["reference_name"]))
            return False

        elif "headgear" in json and not json["headgear"] in __ALL_WEARABLES:
            jn_utils.log("Cannot load outfit {0} as specified headgear does not exist.".format(json["reference_name"]))
            return False

        elif "necklace" in json and not json["necklace"] in __ALL_WEARABLES:
            jn_utils.log("Cannot load outfit {0} as specified necklace does not exist.".format(json["reference_name"]))
            return False

        elif "facewear" in json and not json["facewear"] in __ALL_WEARABLES:
            jn_utils.log("Cannot load outfit {0} as specified facewear does not exist.".format(json["reference_name"]))
            return False

        elif "back" in json and not json["back"] in __ALL_WEARABLES:
            jn_utils.log("Cannot load outfit {0} as specified back does not exist.".format(json["reference_name"]))
            return False

        else:
            outfit = JNOutfit(
                reference_name=json["reference_name"],
                display_name=json["display_name"],
                unlocked=json["unlocked"],
                is_jn_outfit=False,
                clothes=__ALL_WEARABLES[json["clothes"]],
                hairstyle=__ALL_WEARABLES[json["hairstyle"]],
                accessory=__ALL_WEARABLES[json["accessory"]] if "accessory" in json else None,
                eyewear=__ALL_WEARABLES[json["eyewear"]] if "eyewear" in json else None,
                headgear=__ALL_WEARABLES[json["headgear"]] if "headgear" in json else None,
                necklace=__ALL_WEARABLES[json["necklace"]]  if "necklace" in json else None,
                facewear=__ALL_WEARABLES[json["facewear"]]  if "facewear" in json else None,
                back=__ALL_WEARABLES[json["back"]]  if "back" in json else None
            )

            # Sanity check components to make sure the components are applicable to the slots they have been assigned to
            if not isinstance(outfit.clothes, JNClothes):
                jn_utils.log("Cannot load outfit {0} as specified clothes are not valid clothing.".format(outfit.reference_name))
                return False

            elif not isinstance(outfit.hairstyle, JNHairstyle):
                jn_utils.log("Cannot load outfit {0} as specified hairstyle is not a valid hairstyle.".format(outfit.reference_name))
                return False

            elif outfit.accessory and not isinstance(outfit.accessory, JNAccessory):
                jn_utils.log("Cannot load outfit {0} as specified accessory is not a valid accessory.".format(outfit.reference_name))
                return False

            elif outfit.eyewear and not isinstance(outfit.eyewear, JNEyewear):
                jn_utils.log("Cannot load outfit {0} as specified eyewear is not valid eyewear.".format(outfit.reference_name))
                return False

            elif outfit.headgear and not isinstance(outfit.headgear, JNHeadgear):
                jn_utils.log("Cannot load outfit {0} as specified headgear is not valid headgear.".format(outfit.reference_name))
                return False

            elif outfit.necklace and not isinstance(outfit.necklace, JNNecklace):
                jn_utils.log("Cannot load outfit {0} as specified necklace is not a valid necklace.".format(outfit.reference_name))
                return False

            elif outfit.facewear and not isinstance(outfit.facewear, JNFacewear):
                jn_utils.log("Cannot load outfit {0} as specified facewear is not a valid facewear.".format(outfit.reference_name))
                return False

            elif outfit.back and not isinstance(outfit.back, JNBack):
                jn_utils.log("Cannot load outfit {0} as specified back is not a valid back.".format(outfit.reference_name))
                return False

            # Make sure locks aren't being bypassed with this outfit by locking the outfit if any components are locked
            if outfit.unlocked:
                if (
                    not outfit.clothes.unlocked
                    or not outfit.hairstyle.unlocked
                    or outfit.accessory and not outfit.accessory.unlocked
                    or outfit.eyewear and not outfit.eyewear.unlocked
                    or outfit.headgear and not outfit.headgear.unlocked
                    or outfit.necklace and not outfit.necklace.unlocked
                    or outfit.facewear and not outfit.facewear.unlocked
                    or outfit.back and not outfit.back.unlocked
                ):
                    jn_utils.log("Outfit {0} contains one or more locked components; locking outfit.".format(outfit.reference_name))
                    outfit.unlocked = False

            __register_outfit(outfit)
            return True

    def _clear_outfit_list():
        """
        Clears the list of outfits stored in memory, so it can be reloaded.
        """
        __ALL_WEARABLES = {}

    def _clear_wearable_list():
        """
        Clears the list of wearables stored in memory, so it can be reloaded.
        """
        __ALL_OUTFITS = {}

    def load_custom_outfits():
        """
        Loads the custom wearables from the game/outfits directory.
        """
        if jn_utils.createDirectoryIfNotExists(__CUSTOM_OUTFITS_DIRECTORY):
            jn_utils.log("Unable to load custom outfits as the directory does not exist, and had to be created.")
            return

        outfit_files = jn_utils.getAllDirectoryFiles(__CUSTOM_OUTFITS_DIRECTORY, ["json"])
        success_count = 0

        for file_name, file_path in outfit_files:
            try:
                with open(file_path) as outfit_data:
                    if _load_outfit_from_json(json.loads(outfit_data.read())):
                        success_count += 1

            except OSError:
                jn_utils.log("Unable to read file {0}; file could not be found.".format(file_name))

            except TypeError:
                jn_utils.log("Unable to read file {0}; corrupt file or invalid JSON.".format(file_name))

            except ValueError:
                jn_utils.log("Unable to read file {0}; corrupt file or invalid JSON.".format(file_name))

            except:
                raise

        if success_count != len(outfit_files):
            renpy.notify("One or more outfits failed to load; please check log for more information.")

    def load_custom_wearables():
        """
        Loads the custom wearables from the game/wearables directory.
        """
        if jn_utils.createDirectoryIfNotExists(__CUSTOM_WEARABLES_DIRECTORY):
            jn_utils.log("Unable to load custom wearables as the directory does not exist, and had to be created.")
            return

        wearable_files = jn_utils.getAllDirectoryFiles(__CUSTOM_WEARABLES_DIRECTORY, ["json"])
        success_count = 0

        for file_name, file_path in wearable_files:
            try:
                with open(file_path) as wearable_data:
                    if _load_wearable_from_json(json.loads(wearable_data.read())):
                        success_count += 1

            except OSError:
                jn_utils.log("Unable to read file {0}; file could not be found.".format(file_name))

            except TypeError:
                jn_utils.log("Unable to read file {0}; corrupt file or invalid JSON.".format(file_name))

            except ValueError:
                jn_utils.log("Unable to read file {0}; corrupt file or invalid JSON.".format(file_name))

            except:
                raise

        if success_count != len(wearable_files):
            renpy.notify("One or more wearables failed to load; please check log for more information.")

    def unload_custom_outfits():
        """
        Unloads all custom outfits from active memory.
        """
        __ALL_OUTFITS = JNOutfit.filter_outfits(
            outfit_list=get_all_outfits(),
            is_jn_outfit=True)

    def unload_custom_wearables():
        """
        Unloads all custom wearables from active memory.
        """
        __ALL_WEARABLES = JNWearable.filter_wearables(
            wearable_list=get_all_wearables(),
            is_jn_wearable=True)

        return

    def outfit_exists(outfit_name):
        """
        Returns whether the given outfit exists in the list of registered outfits.

        IN:
            - outfit_name - str outfit name to search for

        OUT: True if it exists, otherwise False
        """
        return outfit_name in __ALL_OUTFITS

    def wearable_exists(wearable_name):
        """
        Returns whether the given outfit exists in the list of registered outfits.

        IN:
            - wearable_name - str wearable name to search for

        OUT: True if it exists, otherwise False
        """
        return wearable_name in __ALL_WEARABLES

    def get_outfit(outfit_name):
        """
        Returns the outfit for the given name, if it exists.

        IN:
            - outfit_name - str outfit name to fetch

        OUT: Corresponding JNOutfit if the outfit exists, otherwise None
        """
        if outfit_exists(outfit_name):
            return __ALL_OUTFITS[outfit_name]

        return None

    def get_wearable(wearable_name):
        """
        Returns the outfit for the given name, if it exists.

        IN:
            - wearable_name - str wearable name to fetch

        OUT: Corresponding JNWearable child if the wearable exists, otherwise None
        """
        if wearable_exists(wearable_name):
            return __ALL_WEARABLES[wearable_name]

        return None

    def get_all_outfits():
        """
        Returns a list of all outfits.
        """
        return __ALL_OUTFITS.values()

    def get_all_wearables():
        """
        Returns a list of all outfits.
        """
        return __ALL_WEARABLES.values()

    def save_temporary_outfit(outfit):
        """
        Saves the given outfit as the designated temporary outfit.
        The temporary outfit is not persisted between game exit/reload.

        IN:
            - outfit - the JNOutfit to use as the base for the temporary outfit
        """
        temporary_outfit = get_outfit("jn_temporary_outfit")
        temporary_outfit.clothes = outfit.clothes
        temporary_outfit.hairstyle = outfit.hairstyle
        temporary_outfit.accessory = get_wearable("jn_none") if not outfit.accessory else outfit.accessory
        temporary_outfit.eyewear = get_wearable("jn_none") if not outfit.eyewear else outfit.eyewear
        temporary_outfit.headgear = get_wearable("jn_none") if not outfit.headgear else outfit.headgear
        temporary_outfit.necklace = get_wearable("jn_none") if not outfit.necklace else outfit.necklace
        temporary_outfit.facewear = get_wearable("jn_none") if not outfit.facewear else outfit.facewear
        temporary_outfit.back = get_wearable("jn_none") if not outfit.back else outfit.back

        store.Natsuki.setOutfit(temporary_outfit, persist=False)

        return True

    def save_custom_outfit(outfit):
        """
        Saves the given outfit as a JSON custom outfit file.

        IN:
            - outfit - the JNOutfit to save
        """
        # Create a new custom outfit, templating the old one
        new_custom_outfit = JNOutfit(
            reference_name="{0}_{1}_{2}".format(
                store.persistent.playername,
                outfit.display_name.replace(" ", "_"),
                int(time.time())
            ).lower(),
            display_name=outfit.display_name,
            unlocked=True,
            is_jn_outfit=False,
            clothes=outfit.clothes,
            hairstyle=outfit.hairstyle,
            accessory=outfit.accessory,
            eyewear=outfit.eyewear,
            headgear=outfit.headgear,
            necklace=outfit.necklace,
            facewear=outfit.facewear,
            back=outfit.back
        )

        # Create directory if it doesn't exist
        if jn_utils.createDirectoryIfNotExists(__CUSTOM_OUTFITS_DIRECTORY):
            jn_utils.log("custom_outfits directory was not found and had to be created.")

        try:
            # Create the JSON file
            with open(os.path.join(__CUSTOM_OUTFITS_DIRECTORY, "{0}.json".format(new_custom_outfit.reference_name)), "w") as file:
                file.write(new_custom_outfit.to_json_string())

            # Finally register the new outfit
            __register_outfit(outfit=new_custom_outfit, player_created=True)
            store.Natsuki.setOutfit(new_custom_outfit)
            renpy.notify("Outfit saved!")
            return True

        except Exception as exception:
            renpy.notify("Save failed; please check log for more information.")
            jn_utils.log("Failed to save outfit {0}, as a write operation was not possible.".format(new_custom_outfit.display_name))
            return False

    def delete_custom_outfit(outfit):
        """
        Removes the given outfit from the list of all outfits, and removes its persistent data.
        You should check to make sure Natsuki isn't wearing the outfit first.

        IN:
            - outfit - the JNOutfit to delete
        """
        # Create directory if it doesn't exist
        if jn_utils.createDirectoryIfNotExists(__CUSTOM_OUTFITS_DIRECTORY):
            jn_utils.log("custom_outfits directory was not found and had to be created.")

        # We can't delete the file for some reason, so abort the deletion process
        elif not jn_utils.deleteFileFromDirectory(
            path=os.path.join(__CUSTOM_OUTFITS_DIRECTORY, "{0}.json".format(outfit.reference_name))
        ):
            renpy.notify("Delete failed; please check log for more information.")
            jn_utils.log("Failed to delete outfit {0}, as a remove operation was not possible.".format(outfit.display_name))
            return False

        else:
            # We deleted the file; finally remove the outfit from runtime and persistent
            __delete_outfit(outfit)
            renpy.notify("Outfit deleted!")
            return True

    def get_realtime_outfit():
        """
        Returns an outfit based on the time of day, weekday/weekend and affinity.
        """
        if store.Natsuki.isAffectionate(higher=True):
            if store.jn_is_weekday():
                return _OUTFIT_SCHEDULE_WEEKDAY_HIGH_AFFINITY.get(store.jn_get_current_time_block())

            else:
                return _OUTFIT_SCHEDULE_WEEKEND_HIGH_AFFINITY.get(store.jn_get_current_time_block())

        elif store.Natsuki.isUpset(higher=True):
            if store.jn_is_weekday():
                return _OUTFIT_SCHEDULE_WEEKDAY_MEDIUM_AFFINITY.get(store.jn_get_current_time_block())

            else:
                return _OUTFIT_SCHEDULE_WEEKEND_MEDIUM_AFFINITY.get(store.jn_get_current_time_block())

        else:
            if store.jn_is_weekday():
                return _OUTFIT_SCHEDULE_WEEKDAY_LOW_AFFINITY.get(store.jn_get_current_time_block())

            else:
                return _OUTFIT_SCHEDULE_WEEKEND_LOW_AFFINITY.get(store.jn_get_current_time_block())

    # Placeholder
    __register_wearable(JNWearable(
        reference_name="jn_none",
        display_name="None",
        unlocked=False,
        is_jn_wearable=True,
    ))

    # Official JN hairstyles
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_bedhead",
        display_name="Bedhead",
        unlocked=True,
        is_jn_wearable=True,
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_bun",
        display_name="Bun",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_twintails",
        display_name="Twintails with red ribbons",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_down",
        display_name="Down",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_messy_bun",
        display_name="Messy bun",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_ponytail",
        display_name="Ponytail",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_super_messy",
        display_name="Super messy",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_princess_braids",
        display_name="Princess braids",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_low_bun",
        display_name="Low bun",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_pigtails",
        display_name="Pigtails",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_twin_buns",
        display_name="Twin buns",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_down_long",
        display_name="Long hair down",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_pixie_cut",
        display_name="Pixie cut",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_low_hoops",
        display_name="Low hoops",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_high_hoops",
        display_name="High hoops",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_twintails_long",
        display_name="Long hair with twintails",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_twintails_white_ribbons",
        display_name="Twintails with white ribbons",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_wavy",
        display_name="Wavy",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_twintails_braided",
        display_name="Braided twintails",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHairstyle(
        reference_name="jn_hair_twintails_down",
        display_name="Twintails down",
        unlocked=True,
        is_jn_wearable=True
    ))

    # Official JN eyewear
    __register_wearable(JNEyewear(
        reference_name="jn_eyewear_round_glasses_black",
        display_name="Black round glasses",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNEyewear(
        reference_name="jn_eyewear_round_glasses_red",
        display_name="Red round glasses",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNEyewear(
        reference_name="jn_eyewear_round_glasses_brown",
        display_name="Brown round glasses",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNEyewear(
        reference_name="jn_eyewear_round_sunglasses",
        display_name="Round sunglasses",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNEyewear(
        reference_name="jn_eyewear_rectangular_glasses_black",
        display_name="Black rectangular glasses",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNEyewear(
        reference_name="jn_eyewear_rectangular_glasses_red",
        display_name="Red rectangular glasses",
        unlocked=False,
        is_jn_wearable=True
    ))

    # Official JN accessories
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_hairband_gray",
        display_name="Gray hairband",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_hairband_green",
        display_name="Green hairband",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_hairband_hot_pink",
        display_name="Hot pink hairband",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_hairband_purple",
        display_name="Purple hairband",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_hairband_red",
        display_name="Red hairband",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_hairband_white",
        display_name="White hairband",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_purple_rose",
        display_name="Purple rose",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_pink_heart_hairpin",
        display_name="Pink heart hairpin",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_gold_star_hairpin",
        display_name="Gold star hairpin",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_pink_star_hairpin",
        display_name="Pink star hairpin",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_hairband_stars",
        display_name="Stars hairband",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_hairband_cat",
        display_name="Cat hairband",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_double_white_hairbands",
        display_name="Double white hairbands",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_fried_egg_hairpin",
        display_name="Fried egg hairpin",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNAccessory(
        reference_name="jn_accessory_cherry_blossom_hairpin",
        display_name="Cherry blossom hairpin",
        unlocked=False,
        is_jn_wearable=True
    ))

    # Official JN clothes
    __register_wearable(JNClothes(
        reference_name="jn_clothes_school_uniform",
        display_name="School uniform",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_casual",
        display_name="Casual clothes",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_heart_sweater",
        display_name="Heart sweater",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_magical_girl",
        display_name="Magical girl cosplay",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_rose_lace_dress",
        display_name="Rose lace dress",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_sango_cosplay",
        display_name="Sango cosplay",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_star_pajamas",
        display_name="Star pajamas",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_trainer_cosplay",
        display_name="Trainer cosplay",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_lolita_christmas_dress",
        display_name="Lolita Christmas dress",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_lolita_school_uniform",
        display_name="Lolita school uniform",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_nya_sweater",
        display_name="Nya! sweater",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_pastel_goth_overalls",
        display_name="Pastel goth overalls",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_qeeb_sweater",
        display_name="Qeeb sweater",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_qt_sweater",
        display_name="QT sweater",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_ruffled_swimsuit",
        display_name="Ruffled swimsuit",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_bee_off_shoulder_sweater",
        display_name="Bee off-shoulder sweater",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_autumn_off_shoulder_sweater",
        display_name="Autumn off-shoulder sweater",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_creamsicle_off_shoulder_sweater",
        display_name="Creamsicle off-shoulder sweater",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_nightbloom_off_shoulder_sweater",
        display_name="Nightbloom off-shoulder sweater",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_hoodie_not_cute",
        display_name="'Not cute' hoodie",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_hoodie_turtleneck",
        display_name="Turtleneck hoodie",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_skater_shirt",
        display_name="Skater shirt",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_cosy_cardigan",
        display_name="Cosy cardigan",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_bunny_pajamas",
        display_name="Bunny pajamas",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_ruffle_neck_sweater",
        display_name="Ruffle neck sweater",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_chocolate_plaid_dress",
        display_name="Chocolate plaid dress",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_office_blazer",
        display_name="Office blazer",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_chick_dress",
        display_name="Chick dress",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNClothes(
        reference_name="jn_clothes_cherry_blossom_dress",
        display_name="Cherry Blossom dress",
        unlocked=False,
        is_jn_wearable=True
    ))

    # Official JN headgear

    # Hats/hairbands/ears
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_santa_hat",
        display_name="Santa hat",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_trainer_hat",
        display_name="Trainer hat",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_cat_ears",
        display_name="Cat ears",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_fox_ears",
        display_name="Fox ears",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_basic_white_headband",
        display_name="Basic white headband",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_cat_headband",
        display_name="Cat headband",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_purple_rose_headband",
        display_name="Purple rose headband",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_spiked_headband",
        display_name="Spiked headband",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_bee_headband",
        display_name="Bee headband",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_black_beanie",
        display_name="Black beanie",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_hairtie",
        display_name="Hairtie",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_teddy_hairpins",
        display_name="Teddy hairpins",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_sleep_mask",
        display_name="Sleep mask",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_classic_party_hat",
        display_name="Classic party hat",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_new_year_headband",
        display_name="New year headband",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_chocolate_plaid_bow",
        display_name="Chocolate plaid bow",
        unlocked=False,
        is_jn_wearable=True
    ))

    # Ahoges
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_ahoge_curly",
        display_name="Ahoge (curly)",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_ahoge_small",
        display_name="Ahoge (small)",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_ahoge_swoop",
        display_name="Ahoge (swoop)",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_ahoge_double",
        display_name="Ahoge (double)",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_ahoge_simple",
        display_name="Ahoge (simple)",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_ahoge_heart",
        display_name="Ahoge (heart)",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_ahoge_swirl",
        display_name="Ahoge (swirl)",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNHeadgear(
        reference_name="jn_headgear_pompoms",
        display_name="Pompoms",
        unlocked=False,
        is_jn_wearable=True
    ))

    # Official JN necklaces
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_bell_collar",
        display_name="Bell collar",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_plain_choker",
        display_name="Plain choker",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_pink_scarf",
        display_name="Pink scarf",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_spiked_choker",
        display_name="Spiked choker",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_thin_choker",
        display_name="Thin choker",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_black_choker",
        display_name="Black choker",
        unlocked=True,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_sango_choker",
        display_name="Sango choker",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_twirled_choker",
        display_name="Twirled choker",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_golden_necklace",
        display_name="Golden necklace",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_formal_necktie",
        display_name="Formal necktie",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNNecklace(
        reference_name="jn_necklace_bunny_necklace",
        display_name="Bunny necklace",
        unlocked=False,
        is_jn_wearable=True
    ))

    # Official JN facewear
    __register_wearable(JNFacewear(
        reference_name="jn_facewear_sprinkles",
        display_name="Sprinkles",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNFacewear(
        reference_name="jn_facewear_plasters",
        display_name="Plasters",
        unlocked=False,
        is_jn_wearable=True
    ))

    # Official JN back items
    __register_wearable(JNBack(
        reference_name="jn_back_cat_tail",
        display_name="Cat tail",
        unlocked=False,
        is_jn_wearable=True
    ))
    __register_wearable(JNBack(
        reference_name="jn_back_fox_tail",
        display_name="Fox tail",
        unlocked=False,
        is_jn_wearable=True
    ))

    # Starter official JN outfits
    __register_outfit(JNOutfit(
        reference_name="jn_school_uniform",
        display_name="School uniform",
        unlocked=True,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_school_uniform"),
        hairstyle=get_wearable("jn_hair_twintails"),
        accessory=get_wearable("jn_accessory_hairband_red")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_casual_clothes",
        display_name="Casual clothes",
        unlocked=True,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_casual"),
        hairstyle=get_wearable("jn_hair_bun"),
        accessory=get_wearable("jn_accessory_hairband_white")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_star_pajamas",
        display_name="Star pajamas",
        unlocked=True,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_star_pajamas"),
        hairstyle=get_wearable("jn_hair_down"),
        accessory=get_wearable("jn_accessory_hairband_hot_pink")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_bunny_pajamas",
        display_name="Bunny pajamas",
        unlocked=True,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_bunny_pajamas"),
        hairstyle=get_wearable("jn_hair_down"),
        headgear=get_wearable("jn_headgear_sleep_mask")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_hoodie_turtleneck",
        display_name="Hoodie and turtleneck",
        unlocked=True,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_hoodie_turtleneck"),
        hairstyle=get_wearable("jn_hair_bedhead"),
        accessory=get_wearable("jn_accessory_hairband_purple")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_nyatsuki_outfit",
        display_name="Nya! sweater getup",
        unlocked=True,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_nya_sweater"),
        hairstyle=get_wearable("jn_hair_twintails"),
        headgear=get_wearable("jn_headgear_cat_headband"),
        accessory=get_wearable("jn_accessory_hairband_cat"),
        necklace=get_wearable("jn_necklace_bell_collar")
    ))

    # Unlockable official JN default outfits
    __register_outfit(JNOutfit(
        reference_name="jn_formal_dress",
        display_name="Formal dress",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_rose_lace_dress"),
        hairstyle=get_wearable("jn_hair_ponytail"),
        accessory=get_wearable("jn_accessory_purple_rose")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_christmas_outfit",
        display_name="Christmas outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_lolita_christmas_dress"),
        hairstyle=get_wearable("jn_hair_twintails"),
        accessory=get_wearable("jn_accessory_hairband_red"),
        headgear=get_wearable("jn_headgear_pompoms")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_trainer_cosplay",
        display_name="Trainer cosplay",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_trainer_cosplay"),
        hairstyle=get_wearable("jn_hair_down"),
        accessory=get_wearable("jn_accessory_hairband_white"),
        headgear=get_wearable("jn_headgear_trainer_hat"),
        necklace=get_wearable("jn_necklace_pink_scarf")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_sango_cosplay",
        display_name="Sango cosplay",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_sango_cosplay"),
        hairstyle=get_wearable("jn_hair_twintails"),
        necklace=get_wearable("jn_necklace_sango_choker"),
        accessory=get_wearable("jn_accessory_hairband_purple")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_ruffled_swimsuit",
        display_name="Beach outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_ruffled_swimsuit"),
        hairstyle=get_wearable("jn_hair_down")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_skater_outfit",
        display_name="Skater outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_skater_shirt"),
        hairstyle=get_wearable("jn_hair_twintails_white_ribbons"),
        accessory=get_wearable("jn_accessory_double_white_hairbands"),
        necklace=get_wearable("jn_necklace_twirled_choker"),
        facewear=get_wearable("jn_facewear_plasters")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_cosy_cardigan_outfit",
        display_name="Cosy cardigan outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_cosy_cardigan"),
        accessory=get_wearable("jn_accessory_hairband_red"),
        headgear=get_wearable("jn_headgear_teddy_hairpins"),
        hairstyle=get_wearable("jn_hair_twintails")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_pastel_goth_getup",
        display_name="Pastel goth getup",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_cosy_cardigan"),
        accessory=get_wearable("jn_accessory_hairband_white"),
        hairstyle=get_wearable("jn_hair_twintails"),
        facewear=get_wearable("jn_facewear_sprinkles")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_ruffle_neck_sweater_outfit",
        display_name="Ruffle neck sweater outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_ruffle_neck_sweater"),
        accessory=get_wearable("jn_accessory_hairband_red"),
        hairstyle=get_wearable("jn_hair_twin_buns")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_heart_sweater_outfit",
        display_name="Heart sweater outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_heart_sweater"),
        accessory=get_wearable("jn_accessory_hairband_red"),
        hairstyle=get_wearable("jn_hair_twin_buns")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_chocolate_plaid_collection",
        display_name="Chocolate plaid collection",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_chocolate_plaid_dress"),
        headgear=get_wearable("jn_headgear_chocolate_plaid_bow"),
        necklace=get_wearable("jn_necklace_golden_necklace"),
        hairstyle=get_wearable("jn_hair_ponytail")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_office_outfit",
        display_name="Office outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_office_blazer"),
        hairstyle=get_wearable("jn_hair_wavy"),
        necklace=get_wearable("jn_necklace_formal_necktie")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_chick_outfit",
        display_name="Chick outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_chick_dress"),
        accessory=get_wearable("jn_accessory_fried_egg_hairpin"),
        hairstyle=get_wearable("jn_hair_twintails_braided"),
        necklace=get_wearable("jn_necklace_bunny_necklace")
    ))
    __register_outfit(JNOutfit(
        reference_name="jn_cherry_blossom_outfit",
        display_name="Cherry blossom outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_cherry_blossom_dress"),
        accessory=get_wearable("jn_accessory_cherry_blossom_hairpin"),
        hairstyle=get_wearable("jn_hair_twintails_braided"),
        necklace=get_wearable("jn_necklace_bunny_necklace")
    ))

    # Internal outfits; used for events, etc. These shouldn't be unlocked!

    # Temporary outfit; used when we don't want to visibly save an outfit
    __register_outfit(JNOutfit(
        reference_name="jn_temporary_outfit",
        display_name="Temporary outfit",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_school_uniform"),
        hairstyle=get_wearable("jn_hair_twintails"),
        accessory=get_wearable("jn_accessory_hairband_red")
    ))

    # Outfit used for ahoge unlock event
    __register_outfit(JNOutfit(
        reference_name="jn_ahoge_unlock",
        display_name="Ahoge unlock",
        unlocked=False,
        is_jn_outfit=True,
        clothes=get_wearable("jn_clothes_star_pajamas"),
        hairstyle=get_wearable("jn_hair_super_messy")
    ))

    # Random choice between pajamas
    __PAJAMA_CHOICE = get_outfit("jn_bunny_pajamas") if random.randint(0, 10) == 1 else get_outfit("jn_star_pajamas")

    # Outfit schedules
    _OUTFIT_SCHEDULE_WEEKDAY_HIGH_AFFINITY = {
        store.JNTimeBlocks.early_morning: __PAJAMA_CHOICE,
        store.JNTimeBlocks.mid_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.late_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.afternoon: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.evening: random.choice((get_outfit("jn_casual_clothes"), get_outfit("jn_hoodie_turtleneck"))),
        store.JNTimeBlocks.night: __PAJAMA_CHOICE
    }

    _OUTFIT_SCHEDULE_WEEKEND_HIGH_AFFINITY = {
        store.JNTimeBlocks.early_morning: __PAJAMA_CHOICE,
        store.JNTimeBlocks.mid_morning: __PAJAMA_CHOICE,
        store.JNTimeBlocks.late_morning: __PAJAMA_CHOICE,
        store.JNTimeBlocks.afternoon: get_outfit("jn_casual_clothes"),
        store.JNTimeBlocks.evening: random.choice((get_outfit("jn_casual_clothes"), get_outfit("jn_hoodie_turtleneck"))),
        store.JNTimeBlocks.night: __PAJAMA_CHOICE
    }

    _OUTFIT_SCHEDULE_WEEKDAY_MEDIUM_AFFINITY = {
        store.JNTimeBlocks.early_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.mid_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.late_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.afternoon: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.evening: get_outfit("jn_casual_clothes"),
        store.JNTimeBlocks.night: get_outfit("jn_casual_clothes")
    }

    _OUTFIT_SCHEDULE_WEEKEND_MEDIUM_AFFINITY = {
        store.JNTimeBlocks.early_morning: __PAJAMA_CHOICE,
        store.JNTimeBlocks.mid_morning: get_outfit("jn_casual_clothes"),
        store.JNTimeBlocks.late_morning: get_outfit("jn_casual_clothes"),
        store.JNTimeBlocks.afternoon: get_outfit("jn_casual_clothes"),
        store.JNTimeBlocks.evening: get_outfit("jn_casual_clothes"),
        store.JNTimeBlocks.night: random.choice((get_outfit("jn_casual_clothes"), get_outfit("jn_hoodie_turtleneck")))
    }

    _OUTFIT_SCHEDULE_WEEKDAY_LOW_AFFINITY = {
        store.JNTimeBlocks.early_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.mid_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.late_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.afternoon: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.evening: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.night: get_outfit("jn_casual_clothes")
    }

    _OUTFIT_SCHEDULE_WEEKEND_LOW_AFFINITY = {
        store.JNTimeBlocks.early_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.mid_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.late_morning: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.afternoon: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.evening: get_outfit("jn_school_uniform"),
        store.JNTimeBlocks.night: get_outfit("jn_casual_clothes")
    }

# Asking Natsuki to wear an outfit
label outfits_wear_outfit:
    if not jn_outfits.get_all_outfits():
        # No outfits, no point proceeding
        n 4tnmbo "Huh?{w=0.5}{nw}"
        extend 1fchbg " I don't {i}have{/i} any other outfits,{w=0.2} dummy!"
        jump ch30_loop

    elif len(jn_outfits._SESSION_NEW_UNLOCKS):
        # Automatically go to gifting dialogue if player is trying to immediately see new gifted items
        n 1nsqpu "...Wait.{w=1.25}{nw}"
        extend 3tnmfl " What's {i}that{/i} you're holding?"
        n 1fcstrlesi "At {i}least{/i} show me what it is first!"
        show natsuki 1fcspol

        $ jn_rm_topic_from_event_list("new_wearables_outfits_unlocked")
        jump new_wearables_outfits_unlocked

    n 4unmaj "Huh?{w=0.2} You want me to put on another outfit?"
    n 1fchbg "Sure thing!{w=0.5}{nw}"
    extend 1unmbg " What do you want me to wear?{w=1.5}{nw}"
    show natsuki idle at jn_left

    python:
        # Get unlocked outfits, sort them and generate player options
        options = []
        available_outfits = jn_outfits.JNOutfit.filter_outfits(
            outfit_list=jn_outfits.get_all_outfits(),
            unlocked=True)
        available_outfits.sort(key = lambda option: option.display_name)

        for outfit in available_outfits:
            options.append((jn_utils.escapeRenpySubstitutionString(outfit.display_name), outfit))

        options.insert(0, ("You pick!", "random"))

    call screen scrollable_choice_menu(options, ("Nevermind.", None))
    show natsuki at jn_center

    if isinstance(_return, jn_outfits.JNOutfit):
        # Wear the chosen outfit
        $ outfit_name = _return.display_name.lower()
        n 4unmaj "Oh?{w=0.2} You want me to wear my [outfit_name]?{w=0.5}{nw}"
        extend 1uchbg " Gotcha!"
        n 1nchsm "Just give me a second...{w=2}{nw}"

        play audio clothing_ruffle
        $ Natsuki.setOutfit(_return)
        with Fade(out_time=0.1, hold_time=1, in_time=0.5, color="#181212")

        n 1nchbg "Okaaay!"
        n 4tnmsm "How do I look,{w=0.1} [player]?{w=0.5}{nw}"
        extend 4flldvl " Ehehe."
        $ persistent.jn_natsuki_auto_outfit_change_enabled = False

    elif _return == "random":
        # Wear a random unlocked outfit
        n 1fchbg "You got it!{w=1.5}{nw}"
        extend 3fslss " Now what have we got here...{w=1.5}{nw}"
        n 1ncssr "...{w=1.5}{nw}"
        n 4fnmbg "Aha!{w=1.5}{nw}"
        extend 4fchbg " This'll do.{w=1.5}{nw}"
        extend 1uchsm " One second!"

        play audio clothing_ruffle
        $ Natsuki.setOutfit(
            random.choice(
                jn_outfits.JNOutfit.filter_outfits(
                    outfit_list=jn_outfits.get_all_outfits(),
                    unlocked=True,
                    not_reference_name=Natsuki.getOutfitName())
            )
        )
        with Fade(out_time=0.1, hold_time=1, in_time=0.5, color="#181212")

        n 1nchbg "All done!"
        $ persistent.jn_natsuki_auto_outfit_change_enabled = False

    else:
        # Nevermind
        n 1nnmbo "Oh.{w=1.5}{nw}"
        extend 1nllaj " Well, that's fine."
        n 3nsrpol "I didn't wanna change anyway."

    return

# Asking Natsuki to reload outfits from disk
label outfits_reload:
    n 1fchbg "'Kay!{w=0.5}{nw}"
    extend 1ncsss " Just give me a sec here...{w=1.5}{nw}"

    python:
        # We have to unload outfits before wearables due to dependencies
        jn_outfits.unload_custom_outfits()
        jn_outfits.unload_custom_wearables()

        # We have to load wearables before outfits due to dependencies
        jn_outfits.load_custom_wearables()
        jn_outfits.load_custom_outfits()

        # Now we've loaded back into memory, reload the persisted data
        jn_outfits.JNWearable.load_all()
        jn_outfits.JNOutfit.load_all()

    n 1fchsm "...And we're done!"

    return

# Asking Natsuki to suggest a new outfit; leads to the outfit creator flow
label outfits_suggest_outfit:

    if len(jn_outfits._SESSION_NEW_UNLOCKS):
        # Automatically go to gifting dialogue if player is trying to immediately see new gifted items
        n 1nsqpu "...Wait.{w=1.25}{nw}"
        extend 3tnmfl " What's {i}that{/i} you're holding?"
        n 1fcstrlesi "At {i}least{/i} show me what it is first!"
        show natsuki 1fcspol

        $ jn_rm_topic_from_event_list("new_wearables_outfits_unlocked")
        jump new_wearables_outfits_unlocked

    n 4unmaj "Ooh!{w=1.5}{nw}"
    extend 1fchbg " I'm always open to a suggestion!{w=0.5}{nw}"
    extend 1unmss " What did you have in mind?"
    python:
        # We copy these specifically so we can alter them without modifying the outfits in the master list
        import copy
        jn_outfits._LAST_OUTFIT = copy.copy(jn_outfits.get_outfit(Natsuki.getOutfitName()))
        jn_outfits._PREVIEW_OUTFIT = copy.copy(jn_outfits.get_outfit(Natsuki.getOutfitName()))
        jn_outfits._changes_made = False

    show natsuki idle at jn_left
    jump outfits_create_menu

# Asking Natsuki to remove an existing outfit
label outfits_remove_outfit:

    if len(jn_outfits._SESSION_NEW_UNLOCKS):
        # Prevent the player telling Natsuki to delete something she could be about to gift by popping it early, and removing from event list
        n 1nsqpu "...Wait.{w=1.25}{nw}"
        extend 3fnmpo " Are you trying to hide something?"
        n 1fcstrlesi "At least show me what it is first!"
        show natsuki 1fcspol

        $ jn_rm_topic_from_event_list("new_wearables_outfits_unlocked")
        jump new_wearables_outfits_unlocked

    elif (
        not jn_outfits.get_all_outfits()
        or len(jn_outfits.JNOutfit.filter_outfits(
            outfit_list=jn_outfits.get_all_outfits(),
            unlocked=True,
            is_jn_outfit=False)) == 0
    ):
        # No outfits, no point proceeding
        n 1tnmbo "Huh?{w=0.5}{nw}"
        extend 1fchbg " I don't {i}have{/i} any outfit ideas from you to get rid of, dummy!"

        jump ch30_loop

    n 1unmpu "You want me to remove an outfit?{w=0.5}{nw}"
    extend 1nllpu " I guess I can do that."
    n 1nslss "But...{w=1}{nw}"
    extend 1fsrpol " I'm keeping the ones I came up with."

    python:
        # Get unlocked custom outfits, sort them and generate player options
        options = []
        removable_outfits = jn_outfits.JNOutfit.filter_outfits(
            outfit_list=jn_outfits.get_all_outfits(),
            unlocked=True,
            is_jn_outfit=False)

        removable_outfits.sort(key = lambda option: option.display_name)

        for outfit in removable_outfits:
            options.append((jn_utils.escapeRenpySubstitutionString(outfit.display_name), outfit))

    call screen scrollable_choice_menu(options, ("Nevermind.", None))

    if isinstance(_return, jn_outfits.JNOutfit):
        $ outfit_name = _return.display_name.lower()
        n 1unmaj "Oh?{w=0.2} [outfit_name]?{w=0.2} That outfit?"

        menu:
            n "You're sure you want me to remove it?"

            "Yes, remove [outfit_name].":
                if Natsuki.isWearingOutfit(_return.reference_name):
                    # Change Natsuki out of the uniform to be removed, if she's wearing it
                    n 4uwdaj "Oh! I totally forgot I'm wearing it already!"
                    extend 1fslssl " Ehehe."

                    play audio clothing_ruffle
                    $ Natsuki.setOutfit(jn_outfits.get_outfit("jn_casual_clothes"))
                    with Fade(out_time=0.1, hold_time=1, in_time=0.5, color="#181212")

                n 1nchgn "Okaaay!{w=1.5}{nw}"
                extend 1ncsbg " Just give me a second here...{w=1.5}{nw}"

                if jn_outfits.delete_custom_outfit(_return):
                    n 1fchsm "...And it's gone!"

                else:
                    n 1kllaj "...Oh."
                    n 1klrun "Uhmm...{w=1.5}{nw}"
                    extend 4knmpu " [player]?"
                    n 2kllpo "I wasn't able to remove that for some reason."
                    n 2kllss "Sorry..."

            "Nevermind.":
                n 1nnmbo "Oh."
                n 1ullaj "Well...{w=1.5}{nw}"
                extend 1nllca " okay then."

    else:
        n 1nnmbo "Oh.{w=1}{nw}"
        extend 1nchgn " Well,{w=0.1} suits me!"

    jump ch30_loop

# Main outfit creator label
label outfits_create_menu:
    show natsuki idle at jn_left
    call screen create_outfit

# Headgear selection for outfit creator flow
label outfits_create_select_headgear:
    python:
        unlocked_wearables = jn_outfits.JNWearable.filter_wearables(wearable_list=jn_outfits.get_all_wearables(), unlocked=True, wearable_type=jn_outfits.JNHeadgear)
        wearable_options = [(jn_utils.escapeRenpySubstitutionString(wearable.display_name), wearable) for wearable in unlocked_wearables]
        wearable_options.sort(key = lambda option: option[1].display_name)
        wearable_options.insert(0, ("No headgear", "none"))

    call screen scrollable_choice_menu(wearable_options, ("Nevermind.", None))

    if isinstance(_return, basestring) or isinstance(_return, jn_outfits.JNHeadgear):
        play audio clothing_ruffle
        python:
            jn_outfits._changes_made = True
            wearable_to_apply = jn_outfits.get_wearable("jn_none") if _return == "none" else _return
            jn_outfits._PREVIEW_OUTFIT.headgear = wearable_to_apply
            Natsuki.setOutfit(jn_outfits._PREVIEW_OUTFIT)

    jump outfits_create_menu

# Hairstyle selection for outfit creator flow
label outfits_create_select_hairstyle:
    python:
        unlocked_wearables = jn_outfits.JNWearable.filter_wearables(wearable_list=jn_outfits.get_all_wearables(), unlocked=True, wearable_type=jn_outfits.JNHairstyle)
        wearable_options = [(jn_utils.escapeRenpySubstitutionString(wearable.display_name), wearable) for wearable in unlocked_wearables]
        wearable_options.sort(key = lambda option: option[1].display_name)

    call screen scrollable_choice_menu(wearable_options, ("Nevermind.", None))

    if isinstance(_return, jn_outfits.JNHairstyle):
        play audio hair_brush
        python:
            jn_outfits._changes_made = True
            jn_outfits._PREVIEW_OUTFIT.hairstyle = _return
            Natsuki.setOutfit(jn_outfits._PREVIEW_OUTFIT)

    jump outfits_create_menu

# Eyewear selection for outfit creator flow
label outfits_create_select_eyewear:
    python:
        unlocked_wearables = jn_outfits.JNWearable.filter_wearables(wearable_list=jn_outfits.get_all_wearables(), unlocked=True, wearable_type=jn_outfits.JNEyewear)
        wearable_options = [(jn_utils.escapeRenpySubstitutionString(wearable.display_name), wearable) for wearable in unlocked_wearables]
        wearable_options.sort(key = lambda option: option[1].display_name)
        wearable_options.insert(0, ("No eyewear", "none"))

    call screen scrollable_choice_menu(wearable_options, ("Nevermind.", None))

    if isinstance(_return, basestring) or isinstance(_return, jn_outfits.JNEyewear):
        python:
            jn_outfits._changes_made = True
            wearable_to_apply = jn_outfits.get_wearable("jn_none") if _return == "none" else _return
            jn_outfits._PREVIEW_OUTFIT.eyewear = wearable_to_apply
            Natsuki.setOutfit(jn_outfits._PREVIEW_OUTFIT)

    jump outfits_create_menu

# Accessory selection for outfit creator flow
label outfits_create_select_accessory:
    python:
        unlocked_wearables = jn_outfits.JNWearable.filter_wearables(wearable_list=jn_outfits.get_all_wearables(), unlocked=True, wearable_type=jn_outfits.JNAccessory)
        wearable_options = [(jn_utils.escapeRenpySubstitutionString(wearable.display_name), wearable) for wearable in unlocked_wearables]
        wearable_options.sort(key = lambda option: option[1].display_name)
        wearable_options.insert(0, ("No accessory", "none"))

    call screen scrollable_choice_menu(wearable_options, ("Nevermind.", None))

    if isinstance(_return, basestring) or isinstance(_return, jn_outfits.JNAccessory):
        play audio hair_clip
        python:
            jn_outfits._changes_made = True
            wearable_to_apply = jn_outfits.get_wearable("jn_none") if _return == "none" else _return
            jn_outfits._PREVIEW_OUTFIT.accessory = wearable_to_apply
            Natsuki.setOutfit(jn_outfits._PREVIEW_OUTFIT)

    jump outfits_create_menu

# Necklace selection for outfit creator flow
label outfits_create_select_necklace:
    python:
        unlocked_wearables = jn_outfits.JNWearable.filter_wearables(wearable_list=jn_outfits.get_all_wearables(), unlocked=True, wearable_type=jn_outfits.JNNecklace)
        wearable_options = [(jn_utils.escapeRenpySubstitutionString(wearable.display_name), wearable) for wearable in unlocked_wearables]
        wearable_options.sort(key = lambda option: option[1].display_name)
        wearable_options.insert(0, ("No necklace", "none"))

    call screen scrollable_choice_menu(wearable_options, ("Nevermind.", None))

    if isinstance(_return, basestring) or isinstance(_return, jn_outfits.JNNecklace):
        play audio necklace_clip
        python:
            jn_outfits._changes_made = True
            wearable_to_apply = jn_outfits.get_wearable("jn_none") if _return == "none" else _return
            jn_outfits._PREVIEW_OUTFIT.necklace = wearable_to_apply
            Natsuki.setOutfit(jn_outfits._PREVIEW_OUTFIT)

    jump outfits_create_menu

# Clothing selection for outfit creator flow
label outfits_create_select_clothes:
    python:
        unlocked_wearables = jn_outfits.JNWearable.filter_wearables(wearable_list=jn_outfits.get_all_wearables(), unlocked=True, wearable_type=jn_outfits.JNClothes)
        wearable_options = [(jn_utils.escapeRenpySubstitutionString(wearable.display_name), wearable) for wearable in unlocked_wearables]
        wearable_options.sort(key = lambda option: option[1].display_name)

    call screen scrollable_choice_menu(wearable_options, ("Nevermind.", None))

    if isinstance(_return, jn_outfits.JNClothes):
        if (random.choice([True, False])):
            play audio clothing_ruffle
        else:
            play audio zipper

        python:
            jn_outfits._changes_made = True
            jn_outfits._PREVIEW_OUTFIT.clothes = _return
            Natsuki.setOutfit(jn_outfits._PREVIEW_OUTFIT)

    jump outfits_create_menu

# Facewear selection for outfit creator flow
label outfits_create_select_facewear:
    python:
        unlocked_wearables = jn_outfits.JNWearable.filter_wearables(wearable_list=jn_outfits.get_all_wearables(), unlocked=True, wearable_type=jn_outfits.JNFacewear)
        wearable_options = [(jn_utils.escapeRenpySubstitutionString(wearable.display_name), wearable) for wearable in unlocked_wearables]
        wearable_options.sort(key = lambda option: option[1].display_name)
        wearable_options.insert(0, ("No facewear", "none"))

    call screen scrollable_choice_menu(wearable_options, ("Nevermind.", None))

    if isinstance(_return, basestring) or isinstance(_return, jn_outfits.JNFacewear):
        play audio hair_clip
        python:
            jn_outfits._changes_made = True
            wearable_to_apply = jn_outfits.get_wearable("jn_none") if _return == "none" else _return
            jn_outfits._PREVIEW_OUTFIT.facewear = wearable_to_apply
            Natsuki.setOutfit(jn_outfits._PREVIEW_OUTFIT)

    jump outfits_create_menu

# Back slot selection for outfit creator flow
label outfits_create_select_back:
    python:
        unlocked_wearables = jn_outfits.JNWearable.filter_wearables(wearable_list=jn_outfits.get_all_wearables(), unlocked=True, wearable_type=jn_outfits.JNBack)
        wearable_options = [(jn_utils.escapeRenpySubstitutionString(wearable.display_name), wearable) for wearable in unlocked_wearables]
        wearable_options.sort(key = lambda option: option[1].display_name)
        wearable_options.insert(0, ("No back", "none"))

    call screen scrollable_choice_menu(wearable_options, ("Nevermind.", None))

    if isinstance(_return, basestring) or isinstance(_return, jn_outfits.JNBack):
        if (random.choice([True, False])):
            play audio clothing_ruffle
        else:
            play audio zipper

        python:
            jn_outfits._changes_made = True
            wearable_to_apply = jn_outfits.get_wearable("jn_none") if _return == "none" else _return
            jn_outfits._PREVIEW_OUTFIT.back = wearable_to_apply
            Natsuki.setOutfit(jn_outfits._PREVIEW_OUTFIT)

    jump outfits_create_menu

# Exit sequence from the outfit creator flow
label outfits_create_quit:
    if jn_outfits._changes_made:
        n 4unmaj "Huh?{w=0.5}{nw}"
        extend 1tnmbo " You're done already,{w=0.1} [player]?"
        menu:
            n "You're sure you don't want me to try more stuff on?"

            # Go back to editor
            "Yes, I'm not done yet.":
                n 2fcsbg "Gotcha!"
                extend 1tsqsm " What else have you got?"

                jump outfits_create_menu

            # Cancel, ditch the changes
            "No, we're done here.":
                n 1nnmbo "Oh.{w=1.5}{nw}"
                extend 1nllaj " Well...{w=0.3} okay."
                n 2nsrpol "I was bored of changing anyway."

                play audio clothing_ruffle
                $ Natsuki.setOutfit(jn_outfits._LAST_OUTFIT)
                with Fade(out_time=0.1, hold_time=1, in_time=0.5, color="#181212")
                jump ch30_loop

    else:
        n 4tllaj "So...{w=1.5}{nw}"
        extend 3tnmpo " you don't want me to change after all?"
        n 1nlrbo "Huh."
        n 1tnmss "Well,{w=0.1} if it ain't broke,{w=0.1} right?{w=0.5}{nw}"
        extend 2fcssm " Ehehe."
        jump ch30_loop

# Save sequence from the outfit creator flow
label outfits_create_save:
    n 4fllaj "Well,{w=0.5} finally!"
    n 3flrpo "If I'd known you were {i}this{/i} into dress-up,{w=0.3} I'd have set a timer!{w=1.5}{nw}"
    extend 3fsqsm " Ehehe."
    n 1ullaj "So..."
    menu:
        n "All finished, [player]?"

        "Yes, I'd like to save this outfit.":
            n 1fchbg "Gotcha!{w=1.5}{nw}"
            extend 1unmsm " What did you wanna call it?"

            $ name_given = False
            while not name_given:
                $ outfit_name = renpy.input(
                    "What is the name of this outfit?",
                    allow=(jn_globals.DEFAULT_ALPHABETICAL_ALLOW_VALUES+jn_globals.DEFAULT_NUMERICAL_ALLOW_VALUES),
                    length=30
                ).strip()

                # Outfit name cannot be empty or None
                if len(outfit_name) == 0 or outfit_name is None:
                    n 2knmpo "Come on,{w=0.3} [player]!{w=1.5}{nw}"
                    extend 1fchbg " Any outfit worth wearing has a {i}name{/i},{w=0.1} dummy!"

                # Outfit name cannot contain the jn_ namespace, though this should never happen
                elif re.search("^jn_.", outfit_name.lower()):
                    n 1tsqsssbl "...Is that some kind of robot name or something?"
                    n 4fchbl "Try harder,{w=0.2} [player]!"

                # Outfit cannot be an insult or profanity
                elif(
                    jn_utils.get_string_contains_profanity(outfit_name.lower())
                    or jn_utils.get_string_contains_insult(outfit_name.lower())
                ):
                    n 2fsqem "...Really,{w=0.5} [player]."
                    n 1fsqsr "Come on.{w=1}{nw}"
                    extend 1fllsr " Quit being a jerk."

                    $ Natsuki.addApology(jn_apologies.ApologyTypes.rude)
                    $ Natsuki.percentageAffinityLoss(2)

                else:
                    # It's allowed!
                    python:
                        jn_outfits._PREVIEW_OUTFIT.display_name = outfit_name
                        name_given = True

            n 1nchbg "Okaaay!{w=1.5}{nw}"
            extend 1ncsss " Let me just take some notes...{w=1.5}{nw}"

            if jn_outfits.save_custom_outfit(jn_outfits._PREVIEW_OUTFIT):
                n 1uchsm "...And done!"
                n 1fchbg "Thanks,{w=0.1} [player]!{w=0.5}{nw}"
                extend 4uchsm " Ehehe."

                $ jn_outfits._changes_made = False
                jump ch30_loop

            else:
                n 1kllaj "...Oh."
                n 1klrun "Uhmm...{w=1.5}{nw}"
                extend 4knmpu " [player]?"
                n 2kllpo "I wasn't able to save that for some reason."
                n 1kllss "Sorry..."

                jump outfits_create_menu

        "Yes, but don't worry about saving this outfit.":
            n 4tnmpueqm "Eh?{w=0.75}{nw}"
            extend 1tnmaj " You {i}don't{/i} want me to remember this one?"
            n 1ullaj "Well...{w=0.75}{nw}"
            extend 2tnmss " if you insist."
            n 1nchgneme "Less note taking for me!"

            $ jn_outfits._changes_made = False
            $ jn_outfits.save_temporary_outfit(jn_outfits._PREVIEW_OUTFIT)
            jump ch30_loop

        "No, I'm not quite finished.":
            n 3nslpo "I {i}knew{/i} I should have brought a book...{w=2}{nw}"
            extend 1fsqsm " Ehehe."
            n 1ulrss "Well,{w=0.1} whatever.{w=0.5}{nw}"
            extend 4unmbo " What else did you have in mind,{w=0.1} [player]?"

            jump outfits_create_menu

# Natsuki's automatic outfit changes based on time of day, weekday/weekend, affinity
label outfits_auto_change:
    if Natsuki.isEnamored(higher=True):
        n 1uchbg "Oh!{w=0.2} I gotta change,{w=0.1} just give me a sec...{w=0.75}{nw}"

    elif Natsuki.isHappy(higher=True):
        n 4unmpu "Oh!{w=0.2} I should probably change,{w=0.1} one second...{w=0.75}{nw}"
        n 2flrpol "A-{w=0.1}and no peeking,{w=0.1} got it?!{w=0.75}{nw}"

    elif Natsuki.isNormal(higher=True):
        n 4unmpu "Oh -{w=0.1} I gotta get changed.{w=0.2} I'll be back in a sec.{w=0.75}{nw}"

    elif Natsuki.isDistressed(higher=True):
        n 1nnmsl "Back in a second.{w=0.75}{nw}"

    else:
        n 2fsqsl "I'm changing.{w=0.75}{nw}"

    play audio clothing_ruffle
    $ Natsuki.setOutfit(jn_outfits.get_realtime_outfit())
    with Fade(out_time=0.1, hold_time=1, in_time=0.5, color="#181212")

    if Natsuki.isAffectionate(higher=True):
        n 4uchgn "Ta-da!{w=0.2} There we go!{w=0.2} Ehehe.{w=0.75}{nw}"

    elif Natsuki.isHappy(higher=True):
        n 1nchbg "Okaaay!{w=0.2} I'm back!{w=0.75}{nw}"

    elif Natsuki.isNormal(higher=True):
        n 1nnmsm "And...{w=0.3} all done.{w=0.75}{nw}"

    elif Natsuki.isDistressed(higher=True):
        n 3nllsl "I'm back.{w=0.75}{nw}"

    else:
        n 2fsqsl "...{w=0.75}{nw}"

    show natsuki idle at jn_center
    return

label new_wearables_outfits_unlocked:
    python:
        jn_globals.force_quit_enabled = False
        giftbox = random.choice([
            jn_gifts.GIFT_BLUE,
            jn_gifts.GIFT_GREEN,
            jn_gifts.GIFT_PINK,
            jn_gifts.GIFT_PURPLE,
        ])
        giftbox.present()
        jnPause(2.25)

    if Natsuki.isEnamored(higher=True):
        n 1uskemleex "...!"
        n 4ksrunlsbl "..."
        n 4knmpulsbl "[player]...{w=1.25}{nw}"
        extend 2kllpulsbl " y-{w=0.2}you {i}do{/i} know you don't have to get me stuff just so I like you..."
        n 1knmsllsbr "Right?"

        if jnIsPlayerBirthday():
            n 1uskgslesh "...Wait!{w=0.75}{nw}"
            extend 1knmemlsbl " Y-{w=0.2}you shouldn't even be the one {i}giving{/i} things today anyway!"
            n 2kslemlsbl "...It's {i}weird{/i},{w=0.2} [player]..."
            n 1kslbolsbl "..."

        elif jnIsChristmasEve():
            n 2ksrbofsbl "...Especially tonight,{w=0.3} of all nights..."

        elif jnIsChristmasDay():
            n 4kllajlsbr "A-{w=0.2}and anyway,{w=0.75}{nw}"
            extend 1kwmpulsbl " I'm still not used to getting stuff on Christmas Day..."
            n 2kslsllsbl "..."

        n 1uskemlesusbr "I-{w=0.2}it's not that I don't appreciate it!{w=0.5}{nw}"
        extend 1fcsemless " Don't get me wrong!{w=1}{nw}"
        extend 2knmpoless " I-{w=0.2}I totally do!"
        n 1kllemless "I just..."
        n 2ksrunlsbl "..."
        n 1fcsunl "I...{w=0.3} know...{w=1}{nw}"
        extend 2ksrpolsbr " I can't exactly return the favour."
        n 1fcsajlsbl "A-{w=0.2}and you've already done a lot for me,{w=0.5}{nw}"
        extend 4kslbolsbl " so..."
        n 1kcsbolsbl "..."
        n 1kcsemlesi "...Fine.{w=0.75}{nw}"
        extend 1ksrsl " I'll take a look.{w=1.25}{nw}"
        extend 2kslpo " But I still kinda feel like a jerk about it..."

    elif Natsuki.isAffectionate(higher=True):
        n 1uskeml "H-{w=0.2}huh?"
        n 1uskwrl "[player]?{w=1}{nw}"
        extend 4knmwrl " D-{w=0.2}did you {i}seriously{/i} just get me all this stuff?!"
        n 1fslunl "..."
        n 2fcsanl "Uuuuuuuuu-!"
        n 4fpawrledr "Why would you do thaaat?!{w=1}{nw}"

        if jnIsPlayerBirthday():
            n 1uskwrlesh "E-{w=0.2}especially today!{w=1}{nw}"
            extend 4kbkwrl " Did you {i}forget{/i} it's your {i}birthday{/i}?!"

        elif jnIsChristmasEve():
            extend 1fllemf " I-{w=0.2}I mean..."
            n 4knmgsf "Y-{w=0.2}you couldn't have at {i}least{/i} waited for tomorrow?!{w=1}{nw}"
            extend 4kbkwrlesd " I didn't even make a list or anythiiiing!"

        elif jnIsChristmasDay():
            extend 1kllemf " I mean..."
            n 4kwmunlsbl "You should know I'm not used to getting stuff on Christmas Day..."

        else:
            extend 1kbkwrless " I-{w=0.2}I didn't even {i}ask{/i} for anything!"

        n 2fslunl "..."
        n 2fcseml "Jeez...{w=0.5}{nw}"
        extend 1flrsrf " and now I look like a total {i}jerk{/i} for not even having anything to give back...{w=1}{nw}"
        extend 4fsqsrfsbr " I hope you're happy,{w=0.1} [player]."
        n 1fcsemlesisbr "..."
        n 1kcsbolsbr "...Alright.{w=0.75}{nw}"
        extend 2fslpolsbr " J-{w=0.2}just a quick look..."

    else:
        n 1uwdeml "...Eh?"
        n 1ulreml "What even..."
        n 4uskemfeex "...!"
        $ player_initial = jn_utils.getPlayerInitial()
        n 1fbkwrf "[player_initial]-{w=0.2}[player]!"
        n 1kbkwrf "What even {i}is{/i} all this?!"

        if jnIsChristmasEve():
            n 1knmgsf "A-{w=0.2}and come {i}on{/i},{w=0.2} [player]!{w=1}{nw}"
            extend 4kbkwrfesd " It isn't even Christmas yeeeet!"

        elif jnIsChristmasDay():
            n 1fcsemfsbl "I-{w=0.2}I mean,{w=0.75}{nw}"
            extend 2kwmemfsbl " I {i}get{/i} what day it is,{w=0.75}{nw}"
            extend 2kslemfsbl " but..."
            n 1kcspufesisbl "..."

        n 1fllemlesssbl "Y-{w=0.2}you better not be trying to win me over with gifts or something!{w=1}{nw}"
        extend 2fcsemlsbr " Yeesh!"
        n 1flremlsbl "I-{w=0.2}I'll have you know I'm a {i}lot{/i} deeper than that!"
        n 1fsqpulsbl "I swear it's like you're trying to embarrass me sometimes...{w=1}{nw}"
        extend 2fslpolsbl " you jerk."
        n 1ksrcalsbl "You {i}know{/i} I can't exactly give anything {i}back{/i},{w=0.1} either..."
        n 1fcscalesssbl "..."
        n 1kcsemlesi "..."
        n 2fslsll "...Fine.{w=1}{nw}"
        extend 1fcseml " Fine!{w=0.75}{nw}"
        extend 1flremlsbr " I'll look at it!{w=1}{nw}"
        extend 2fsrpolsbr " ...But only because you put the effort in."

    python:
        import random
        alt_dialogue = False
        random.shuffle(jn_outfits._SESSION_NEW_UNLOCKS)
        giftbox.open()

    while len(jn_outfits._SESSION_NEW_UNLOCKS) > 0:
        play audio gift_rustle
        $ unlock = jn_outfits._SESSION_NEW_UNLOCKS.pop()
        if (len(jn_outfits._SESSION_NEW_UNLOCKS) == 0):
            $ giftbox.empty()

        n 1tlrbo "..."

        # You can't really gift a hairstyle, so instead Natsuki is given an idea through a note/picture
        if type(unlock) is jn_outfits.JNHairstyle:
            if alt_dialogue:
                n 1unmpuesu "Mmm?{w=1}{nw}"
                extend 4tnmajeqm " A...{w=0.3} note...?"
                n 1tslpu "..."
                n 1unmgsesu "...Oh!{w=1}{nw}"
                extend 1unmbol " You wanted me to try my hair like that?{w=0.5} [unlock.display_name]?"
                n 3nllunl "..."
                n 1nllajl "Well...{w=1}{nw}"
                extend 4nnmajl " okay."

                if Natsuki.isEnamored(higher=True):
                    n 1nlrssl "I {i}suppose{/i} I can give that a shot later."
                    n 4fsqsslsbl "I bet {i}someone{/i} would like that,{w=0.1} huh?{w=0.5}{nw}"
                    extend 4fsldvlsbl " Ehehe..."

                elif Natsuki.isAffectionate(higher=True):
                    n 1nlrpol "I {i}suppose{/i} I can give that a shot later."
                    extend 1nlrsslsbr " Ehehe..."

                else:
                    n 2fcspol "I {i}suppose{/i} I can give that a shot later."
                    n 2flrajl "B-but only because I want to though,{w=0.75}{nw}"
                    extend 1fsrpol " obviously."

            else:
                n 4tnmpueqm "Eh?{w=1}{nw}"
                extend 1tlrpueqm " What's this note doing here...?"
                n 2tllbo "..."
                n 1unmgsesu "W-{w=0.2}woah!"
                n 1flldvl "Heh.{w=0.5}{nw}"
                extend 1fllsslsbr " I gotta admit.{w=1}{nw}"
                extend 3fsrnvlsbr " I never even thought of trying {i}that{/i} with my hair..."
                n 1unmbo "[unlock.display_name],{w=0.1} huh?"
                n 1nllajl "I {i}guess{/i} it might be worth a try..."

                if Natsuki.isEnamored(higher=True):
                    n 4fsqsslsbr "I wonder who'd like {i}that{/i},{w=0.1} though?{w=0.5}{nw}"
                    extend 4fsqsmlsbr " Ehehe..."

                elif Natsuki.isAffectionate(higher=True):
                    n 1nlrsslsbr "We'll see."

                else:
                    n 1fcsgsl "B-{w=0.2}but only out of curiosity!{w=1}{nw}"
                    extend 2fsqpol " Got it?"

        else:
            if Natsuki.isEnamored(higher=True):
                if alt_dialogue:
                    n 1kcsemlesi "Jeez...{w=1}{nw}"
                    extend 3knmpol " why are you trying to spoil me so much?"
                    n 3fllpol "You know I hate being showered in flashy stuff..."
                    n 1kslsrl "..."
                    n 1ksqsrlsbl "...Especially things like this [unlock.display_name]."
                    extend 1kslsslsbl " Even if it is pretty awesome."
                    n 1kslsrl "..."
                    n 1nllajl "I'm...{w=1}{nw}"
                    extend 2ksrpol " just going to keep that too."
                    n 2nsrdvf "...Thanks."

                else:
                    n 1uskgsfesu "...!"
                    n 1fsldvl "...Heh.{w=1}{nw}"
                    extend 4tsqpufsbl " You really {i}are{/i} trying to win me over with all this stuff,{w=0.1} huh?"
                    n 1kslsllsbl "..."
                    n 1fcspulsbl "The [unlock.display_name]...{w=1}{nw}"
                    n 1knmpulsbr "It's...{w=0.5} really nice.{w=0.75}{nw}"
                    extend 4kllsrlsbr " Okay?"
                    n 1kslunlesssbr "Thanks..."

            elif Natsuki.isAffectionate(higher=True):
                if alt_dialogue:
                    n 1uwdajlesu "...!"
                    n 2fcsemlesssbl "A-{w=0.1}ahem!{w=1}{nw}"
                    extend 2fslpol " Another good choice,{w=0.5}{nw}"
                    extend 4fsqpolsbr " I hate to admit."
                    n 1klrbolsbr "..."
                    n 1fcsunlsbr "...Thanks,{w=0.1} [player]."
                    n 1fllunlsbr "For the [unlock.display_name],{w=0.5}{nw}"
                    extend 4fnmpulsbl " I-{w=0.2}I mean."
                    n 1kslpulsbl "It's...{w=1}{nw}"
                    extend 1kslsslsbl " really cool."
                    n 2fslpofsbl "...Thanks."

                else:
                    n 1uwdajledz "...!"
                    n 1fcsunlesdsbl "..."
                    n 1fcssslsbl "Heh,{w=1}{nw}"
                    extend 3fllbglesssbr " a-{w=0.2}and here I was thinking I'd have to teach you {i}everything{/i} about style!"
                    n 3kllsllsbr "..."
                    n 1knmbolsbr "...But thanks,{w=0.3} [player].{w=1}"
                    extend 1flrunlsbr " For the [unlock.display_name]."
                    n 1fcsunlsbr "I...{w=0.75}{nw}"
                    extend 4ksrunfsbl " really appreciate it."

            else:
                if alt_dialogue:
                    n 1uskgslesh "...!"
                    n 4fdwanfess "Nnnnnnn-!"
                    n 1fcsemfesssbl "Y-{w=0.2}you're just lucky you're good at picking out gifts,{w=0.5}{nw}"
                    extend 3fsqpofesssbl " you jerk."
                    n 3fslpofesssbr "I guess I'll {i}have{/i} to keep this [unlock.display_name] now.{w=0.75}{nw}"
                    extend 3fnmpofesssbl " I-{w=0.2}I hope you're happy."

                else:
                    n 1fspgsledz "W-{w=0.2}woah!"
                    n 1uskemfesh "...!"
                    n 4fbkwrf "What?!{w=1}{nw}"
                    extend 4fllwrfeszsbl " Don't look at me like that!"
                    n 1fcseml "I-{w=0.2}I'm glad to see you have {i}some{/i} taste after all to have found this."
                    n 2fllcal "[unlock.display_name],{w=0.1} huh?{w=1}{nw}"
                    extend 2fcscal " I-{w=0.2}I guess I'll keep it around."
                    n 2fcspofess "Juuuust in case."

        $ alt_dialogue = not alt_dialogue

        if len(jn_outfits._SESSION_NEW_UNLOCKS) > 0:
            if Natsuki.isEnamored(higher=True):
                n 1klrpul "...I can't believe there's even more.{w=1}{nw}"
                extend 4fcspul " Jeez,{w=0.1} [player]..."
                n 4kcspul "...Okay.{w=1}{nw}"
                extend 4fslssl " Let's see what's next..."

            elif Natsuki.isAffectionate(higher=True):
                n 2ksrunl "Uuuuuuu...{w=1}{nw}"
                extend 1ksremlesd " there's {i}still{/i} more?!"
                n 1kcsemlesisbl "Jeez..."

            else:
                n 3fnmpol "H-{w=0.2}how much {i}is{/i} there here,{w=0.1} [player]{w=1}{nw}?"
                extend 3fslpofesssbr " Jeez..."

    if Natsuki.isEnamored(higher=True):
        n 1fcsssl "Finally ran out of things to throw at me,{w=0.5}{nw}"
        extend 1fllsslsbl " huh?"
        n 4kllbolsbl "..."
        n 4ksrpulsbl "I...{w=1}{nw}"
        extend 1ksqsrlsbl " really wish you didn't do that,{w=0.1} you know."
        n 1kllbolsbl "..."
        n 1kllpulsbr "But...{w=0.75}{nw}"
        extend 4knmsslsbr " [player]?"
        n 4fsrunfsbr "..."

        show black zorder JN_BLACK_ZORDER with Dissolve(0.5)
        play audio clothing_ruffle
        $ jnPause(3.5, hard=True)

        if Natsuki.isLove(higher=True):
            show natsuki 1nslunfsbl at jn_center zorder JN_NATSUKI_ZORDER
            play audio kiss
            $ jnPause(1.5, hard=True)
            hide black with Dissolve(1.25)
            $ chosen_tease = jn_utils.getRandomTease()
            n 1knmssf "...Thanks,{w=0.1} [chosen_tease]."
            n 2klrsmfeme "Ehehe."

        else:
            hide black with Dissolve(1.25)
            n 2fslunf "...Thanks.{w=0.75}{nw}"
            extend 2fslsmfsbr " Ehehe."

    elif Natsuki.isAffectionate(higher=True):
        n 1fllun "...Is that it?{w=0.75}{nw}"
        extend 3flrunl " Is that everything?"
        n 1fcsemlesi "Jeez..."
        n 4fnmtrl "You really need to stop giving away so much stuff,{w=0.1} [player].{w=1}{nw}"
        extend 4fsqcal " I don't want you getting into a dumb habit!"
        n 1fslunlsbl "Especially when I can't do anything nice back..."
        n 1kslunlsbl "..."
        n 1kslpulsbl "But...{w=0.75}{nw}"
        extend 4knmsllsbr " [player]?"
        n 2fsrunfsbr "..."

        show black zorder JN_BLACK_ZORDER with Dissolve(0.5)
        show natsuki 1flrcafsbr at jn_center zorder JN_NATSUKI_ZORDER
        play audio clothing_ruffle
        $ jnPause(2, hard=True)
        hide black with Dissolve(1.25)

        n 1ksrcafsbr "..."
        n 1fcstrlsbl "T-{w=0.2}thanks."

    else:
        n 1kslemlesi "Man...{w=1}{nw}"
        extend 2flrtrl " is that all of it?{w=0.5}{nw}"
        extend 1fcspulsbl " Jeez..."
        n 1fslunlsbr "..."
        n 1nslajlsbr "I...{w=0.75}{nw}"
        extend 4nsqajlsbl " suppose I better go put all this away now."
        n 1kslunlsbr "..."
        n 1kslpulsbl "But..."
        extend 4knmsllsbr " [player]?"
        n 2fsrunlsbr "..."
        n 2fsrajlsbr "I..."
        extend 1ksrcafsbr " really appreciate the stuff you got me."
        n 1kllcalsbr "..."
        n 1fcstrlsbl "T-{w=0.2}thanks."

    show black zorder JN_BLACK_ZORDER with Dissolve(0.5)
    $ giftbox.close()
    $ giftbox.hide()
    $ jnPause(2, hard=True)
    play audio chair_out
    $ jnPause(3, hard=True)
    play audio clothing_ruffle
    $ jnPause(1, hard=True)
    play audio drawer
    $ jnPause(1, hard=True)
    $ jnPause(3, hard=True)
    play audio chair_in
    $ jnPause(3, hard=True)
    hide black with Dissolve(1.25)

    n 1ullajl "So..."
    n 4tnmsslsbl "Where we we?{w=1}{nw}"
    extend 4fslsslsbr " Ehehe..."

    $ Natsuki.calculatedAffinityGain(bypass=True)
    $ jn_globals.force_quit_enabled = True

    jump ch30_loop

screen create_outfit():
    if jn_outfits._changes_made:
        text "Unsaved changes!" size 30 xpos 555 ypos 40 style "categorized_menu_button"

    # Outfit controls
    vbox:
        xpos 600
        ypos 140
        hbox:
            # Headgear
            textbutton _("Headgear"):
                style "hkbd_option"
                action Jump("outfits_create_select_headgear")

            label _(jn_utils.escapeRenpySubstitutionString(jn_outfits._PREVIEW_OUTFIT.headgear.display_name) if isinstance(jn_outfits._PREVIEW_OUTFIT.headgear, jn_outfits.JNHeadgear) else "None"):
                style "hkbd_label"
                left_margin 10

        hbox:
            # Hairstyles
            textbutton _("Hairstyles"):
                style "hkbd_option"
                action Jump("outfits_create_select_hairstyle")

            label _(jn_utils.escapeRenpySubstitutionString(jn_outfits._PREVIEW_OUTFIT.hairstyle.display_name)):
                style "hkbd_label"
                left_margin 10

        hbox:
            # Eyewear
            textbutton _("Eyewear"):
                style "hkbd_option"
                action Jump("outfits_create_select_eyewear")

            label _(jn_utils.escapeRenpySubstitutionString(jn_outfits._PREVIEW_OUTFIT.eyewear.display_name) if isinstance(jn_outfits._PREVIEW_OUTFIT.eyewear, jn_outfits.JNEyewear) else "None"):
                style "hkbd_label"
                left_margin 10

        hbox:
            # Facewear
            textbutton _("Facewear"):
                style "hkbd_option"
                action Jump("outfits_create_select_facewear")

            label _(jn_utils.escapeRenpySubstitutionString(jn_outfits._PREVIEW_OUTFIT.facewear.display_name) if isinstance(jn_outfits._PREVIEW_OUTFIT.facewear, jn_outfits.JNFacewear) else "None"):
                style "hkbd_label"
                left_margin 10

        hbox:
            # Accessories
            textbutton _("Accessories"):
                style "hkbd_option"
                action Jump("outfits_create_select_accessory")

            label _(jn_utils.escapeRenpySubstitutionString(jn_outfits._PREVIEW_OUTFIT.accessory.display_name) if isinstance(jn_outfits._PREVIEW_OUTFIT.accessory, jn_outfits.JNAccessory) else "None"):
                style "hkbd_label"
                left_margin 10

        hbox:
            # Necklaces
            textbutton _("Necklaces"):
                style "hkbd_option"
                action Jump("outfits_create_select_necklace")

            label _(jn_utils.escapeRenpySubstitutionString(jn_outfits._PREVIEW_OUTFIT.necklace.display_name) if isinstance(jn_outfits._PREVIEW_OUTFIT.necklace, jn_outfits.JNNecklace) else "None"):
                style "hkbd_label"
                left_margin 10

        hbox:
            # Clothes
            textbutton _("Clothes"):
                style "hkbd_option"
                action Jump("outfits_create_select_clothes")

            label _(jn_utils.escapeRenpySubstitutionString(jn_outfits._PREVIEW_OUTFIT.clothes.display_name)):
                style "hkbd_label"
                left_margin 10

        hbox:
            # Back slot
            textbutton _("Back"):
                style "hkbd_option"
                action Jump("outfits_create_select_back")

            label _(jn_utils.escapeRenpySubstitutionString(jn_outfits._PREVIEW_OUTFIT.back.display_name) if isinstance(jn_outfits._PREVIEW_OUTFIT.back, jn_outfits.JNBack) else "None"):
                style "hkbd_label"
                left_margin 10

    # Save/quit
    vbox:
        xpos 600
        ypos 450
        null height 20

        textbutton _("Finished"):
            style "hkbd_option"
            action Jump("outfits_create_save")

        textbutton _("Quit"):
            style "hkbd_option"
            action Jump("outfits_create_quit")
