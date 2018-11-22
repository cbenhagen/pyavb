from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )

from . import core
from . import utils

from . utils import (
    read_byte,
    read_s8,
    read_bool,
    read_s16le,
    read_u16le,
    read_u32le,
    read_s32le,
    read_string,
    read_doublele,
    read_exp10_encoded_float,
    read_object_ref,
    read_datetime,
    peek_data
)

from . import mobid

class Component(core.AVBObject):
    def read(self, f):
        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x03

        # bob == bytes of binary or bag of bits?
        self.left_bob =  read_object_ref(self.root, f)
        self.right_bob =  read_object_ref(self.root, f)

        self.media_kind_id = read_s16le(f)
        self.edit_rate = read_exp10_encoded_float(f)
        self.name = read_string(f)
        self.effect_id = read_string(f)

        self.attribute_ref = read_object_ref(self.root, f)
        self.session_ref = read_object_ref(self.root, f)

        self.precomputed = read_object_ref(self.root, f)

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x01
        assert version == 0x01

        tag = read_byte(f)
        assert tag == 72

        self.param_list = read_object_ref(self.root, f)

        self.length = 0

    @property
    def media_kind(self):
        if self.media_kind_id   == 0:
            return None
        elif self.media_kind_id   == 1:
            return "picture"
        elif self.media_kind_id == 2:
            return "sound"
        elif self.media_kind_id == 3:
            return "timecode"
        elif self.media_kind_id == 4:
            return "edgecode"
        elif self.media_kind_id == 5:
            return "attribute"
        elif self.media_kind_id == 6:
            return 'effectdata'
        elif self.media_kind_id == 7:
            return 'DescriptiveMetadata'
        else:
            return "unknown%d" % self.media_kind_id

@utils.register_class
class Sequence(Component):
    class_id = b"SEQU"

    def read(self, f):
        super(Sequence, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x03

        count = read_u32le(f)
        self.component_refs = []
        for i in range(count):
            ref = read_object_ref(self.root, f)
            # print ref
            self.component_refs.append(ref)

        tag = read_byte(f)
        assert tag == 0x03

    def components(self):
        for ref in self.component_refs:
            yield ref.value

class Clip(Component):
    def read(self, f):
        super(Clip, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)
        # print self, "0x%02X" % tag, "0x%02X" % version
        assert tag == 0x02
        assert version == 0x01
        self.length = read_u32le(f)

@utils.register_class
class SourceClip(Clip):
    class_id = b'SCLP'
    def read(self, f):
        super(SourceClip, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x03

        mob_id_hi = read_s32le(f)
        mob_id_lo = read_s32le(f)

        self.track_id = read_s16le(f)
        self.start_time = read_s32le(f)
        self.mob_id = mobid.read_mob_id(f)

        # null mobid
        if mob_id_hi == 0 and mob_id_lo == 0:
            self.mob_id = mobid.MobID()

        tag = read_byte(f)
        assert tag == 0x03

@utils.register_class
class Timecode(Clip):
    class_id = b'TCCP'

    def read(self, f):
        super(Timecode, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x01

        # drop ??
        self.flags = read_u32le(f)
        self.fps = read_u16le(f)

        # unused
        f.read(6)

        self.start = read_u32le(f)
        tag = read_byte(f)

        assert tag == 0x03

@utils.register_class
class Edgecode(Clip):
    class_id = b'ECCP'
    def read(self, f):
        super(Edgecode, self).read(f)

@utils.register_class
class TrackRef(Clip):
    class_id = b'TRKR'

@utils.register_class
class ParamClip(Clip):
    class_id = b'PRCL'

@utils.register_class
class Filler(Clip):
    class_id = b'FILL'

    def read(self, f):
        super(Filler, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)
        end_tag = read_byte(f)

        assert tag == 0x02
        assert version == 0x01
        assert end_tag == 0x03

class Track(object):
    def __init__(self):
        self.flags = None
        self.index = None
        self.control_code = None
        self.control_sub_code = None
        self.lock_number = None
        self.refs = []

    @property
    def segment(self):
        for item in self.refs:
            obj = item.value
            if isinstance(obj, Component):
                return obj

class TrackGroup(Component):

    def read(self, f):
        super(TrackGroup, self).read(f)

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x08

        self.mc_mode = read_byte(f)
        self.length = read_s32le(f)
        self.num_scalars = read_s32le(f)

        track_count = read_s32le(f)
        self.tracks = []

        # really annoying, tracks can have variable lengths!!
        has_tracks = True
        for i in range(track_count):
            # print(peek_data(f).encode("hex"))
            track = Track()
            track.flags = read_u16le(f)

            # PVOL has a different track structure
            # contains ref to CTRL and might have 1 or 2 control vars
            if track.flags in (36, 100,):
                ref = read_object_ref(self.root, f)
                track.refs.append(ref)
                track.index = i + 1
                track.control_code = read_s16le(f)
                if track.flags in (100, ):
                    track.control_sub_code = read_s16le(f)
                self.tracks.append(track)
                continue

            track.index = i + 1

            # these flags don't have track label
            # slct_01.chunk
            if track.flags not in (4, 12):
                track.index = read_s16le(f)


            if track.flags == 0 and track.index == 0:
                has_tracks = False
                break

            # print "{0:016b}".format(track.flags)
            # print( str(self.class_id), "index: %04d" % track.index, "flags 0x%04X" % track.flags, track.flags)
            ref_count = 1

            if track.flags in (4, 5):
                ref_count = 1
            elif track.flags in (12, 13, 21, 517,):
                ref_count = 2
            elif track.flags in (29, 519, 525, 533,  ):
                ref_count = 3
            elif track.flags in (541, 527):
                ref_count = 4
            elif track.flags in (543,):
                ref_count = 5
            else:
                raise ValueError("%s: unknown track flag %d" % (str(self.class_id), track.flags))

            for j in range(ref_count):
                ref = read_object_ref(self.root, f)
                track.refs.append(ref)

            self.tracks.append(track)

        tag = read_byte(f)
        version = read_byte(f)
        # print self.tracks, "%02X" % tag
        assert tag == 0x01
        assert version == 0x01

        for i in range(track_count):
            tag = read_byte(f)
            assert tag == 69
            lock =  read_s16le(f)
            if has_tracks:
                self.tracks[i].lock_number = lock

@utils.register_class
class TrackEffect(TrackGroup):
    class_id = b'TKFX'
    def read(self, f):
        super(TrackEffect, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x06

        self.left_length = read_s32le(f)
        self.right_length = read_s32le(f)

        self.info_version = read_s16le(f)
        self.info_current = read_s32le(f)
        self.info_smooth = read_s32le(f)
        self.info_color_item = read_s16le(f)
        self.info_quality = read_s16le(f)
        self.info_is_reversed = read_s8(f)
        self.info_aspect_on = read_bool(f)

        self.keyframes = read_object_ref(self.root, f)
        self.info_force_software = read_bool(f)
        self.info_never_hardware = read_bool(f)

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x01
        assert version == 0x02

        version = read_byte(f)
        assert version == 72
        self.trackman = read_object_ref(self.root, f)

        if self.class_id is b'TKFX':
            tag = read_byte(f)
            assert tag == 0x03

@utils.register_class
class PanVolumeEffect(TrackEffect):
    class_id = b'PVOL'
    def read(self, f):
        super(PanVolumeEffect, self).read(f)
        # print(peek_data(f).encode("hex"))

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x05

        self.level = read_s32le(f)
        self.pan = read_s32le(f)

        self.suppress_validation = read_bool(f)
        self.level_set = read_bool(f)
        self.pan_set = read_bool(f)

        tag = read_byte(f)
        assert tag == 0x01
        tag = read_byte(f)
        assert tag == 0x01

        version = read_byte(f)
        assert version == 71
        self.does_support_seperate_clip_gain = read_s32le(f)

        tag = read_byte(f)
        assert tag == 0x01
        tag = read_byte(f)
        assert tag == 0x02

        version = read_byte(f)
        assert version == 71
        self.is_trim_gain_effect = read_s32le(f)

        tag = read_byte(f)
        assert tag == 0x03

@utils.register_class
class RepSet(TrackGroup):
    class_id = b'RSET'
    def read(self, f):
        super(RepSet, self).read(f)

        # print(peek_data(f).encode("hex"))
        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x01

        # extension
        tag = read_byte(f)
        assert tag == 0x01

        tag = read_byte(f)
        assert tag == 0x01

        version = read_byte(f)
        assert version == 71

        self.rep_set_type = read_s32le(f)

        tag = read_byte(f)
        assert tag == 0x03

#abstract?
class TimeWarp(TrackGroup):
    class_id = b'WARP'

    def read(self, f):
        super(TimeWarp, self).read(f)

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x02
        self.phase_offset = read_s32le(f)

@utils.register_class
class CaptureMask(TimeWarp):
    class_id = b'MASK'
    def read(self, f):
        super(CaptureMask, self).read(f)
        # print(peek_data(f).encode("hex"))

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x01

        self.is_double = read_bool(f)
        self.mask_bits = read_u32le(f)

        tag = read_byte(f)
        assert tag == 0x03

@utils.register_class
class MotionEffect(TimeWarp):
    class_id = b'SPED'
    def read(self, f):
        super(MotionEffect, self).read(f)
        # print(peek_data(f).encode("hex"))

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x03

        num = read_s32le(f)
        den = read_s32le(f)
        self.rate = [num, den]

        tag = read_byte(f)
        assert tag == 0x01

        tag = read_byte(f)
        assert tag == 0x01

        version = read_byte(f)
        assert version == 75
        self.offset_adjust = read_doublele(f)

        tag = read_byte(f)
        assert tag == 0x01

        tag = read_byte(f)
        assert tag == 0x02

        version = read_byte(f)
        assert version == 72
        self.source_param_list = read_object_ref(self.root, f)

        tag = read_byte(f)
        assert tag == 0x01

        tag = read_byte(f)
        assert tag == 0x03

        version = read_byte(f)
        assert version == 66

        self.new_source_calculation = read_bool(f)

        tag = read_byte(f)
        assert tag == 0x03

@utils.register_class
class Repeat(TimeWarp):
    class_id = b'REPT'
    def read(self, f):
        super(Repeat, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)
        assert tag == 0x02
        assert version == 0x01

        tag = read_byte(f)
        assert tag == 0x03


@utils.register_class
class TransistionEffect(TrackGroup):
    class_id = b'TNFX'
    def read(self, f):
        super(TransistionEffect, self).read(f)

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x01

        self.cutpoint = read_s32le(f)

        # the rest is the same as TKFX
        tag = read_byte(f)
        version = read_byte(f)
        assert tag == 0x02
        assert version == 0x05

        self.left_length = read_s32le(f)
        self.right_length = read_s32le(f)

        self.info_version = read_s16le(f)
        self.info_current = read_s32le(f)
        self.info_smooth = read_s32le(f)
        self.info_color_item = read_s16le(f)
        self.info_quality = read_s16le(f)
        self.info_is_reversed = read_s8(f)
        self.info_aspect_on = read_bool(f)

        self.keyframes = read_object_ref(self.root, f)
        self.info_force_software = read_bool(f)
        self.info_never_hardware = read_bool(f)

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x01
        assert version == 0x01

        version = read_byte(f)
        assert version == 72
        self.trackman = read_object_ref(self.root, f)

        tag = read_byte(f)

        assert tag == 0x03

@utils.register_class
class Selector(TrackGroup):
    class_id = b'SLCT'

    def read(self, f):
        super(Selector, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x01

        something = read_byte(f)
        self.selected = read_u16le(f)

        assert self.selected < len(self.tracks)

        tag = read_byte(f)
        assert tag == 0x03

    def components(self):
        for track in self.tracks:
            yield track.segment

@utils.register_class
class Composition(TrackGroup):
    class_id = b'CMPO'

    def read(self, f):
        super(Composition, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)
        assert tag == 0x02
        assert version == 0x02

        mob_id_hi = read_s32le(f)
        mob_id_lo = read_s32le(f)
        last_modified = read_s32le(f)

        self.mob_type_id = read_byte(f)
        self.usage_code =  read_s32le(f)
        self.descriptor = read_object_ref(self.root, f)

        tag = read_byte(f)
        version = read_byte(f)
        assert tag == 0x01
        assert version == 0x01

        tag = read_byte(f)
        assert tag == 71

        creation_time = read_datetime(f)
        self.mob_id = mobid.read_mob_id(f)

        assert read_byte(f) == 0x03

    @property
    def mob_type(self):
        if self.mob_type_id == 1:
            return "CompositionMob"
        elif self.mob_type_id == 2:
            return "MasterMob"
        elif self.mob_type_id == 3:
            return "SourceMob"
        else:
            raise ValueError("Unknown mob type id: %d" % self.mob_type_id)
