from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )

from . import core
from .core import AVBPropertyDef
from .components import Component
from . import utils
from . import mobid

from . utils import (
    read_byte,
    read_s8,
    read_bool,
    read_s16le,
    read_u16le,
    read_u32le,
    read_s32le,
    read_s64le,
    read_string,
    read_doublele,
    read_exp10_encoded_float,
    read_object_ref,
    read_datetime,
    iter_ext,
    read_assert_tag,
    peek_data
)

class Track(core.AVBObject):
    propertydefs = [
        AVBPropertyDef('flags',            'OMFI:TRAK:OptFlags',       'int16'),
        AVBPropertyDef('index',            'OMFI:TRAK:LabelNumber',    'int16'),
        AVBPropertyDef('session_attr',     'OMFI:TRAK:SessionAttrs',   'reference'),
        AVBPropertyDef('component',        'OMFI:TRAK:TrackComponent', 'reference'),
        AVBPropertyDef('filler_proxy',     'OMFI:TRAK:FillerProxy',    'reference'),
        AVBPropertyDef('bob_data',         '__OMFI:TRAK:Bob',          'reference'),
        AVBPropertyDef('control_code',     'OMFI:TRAK:ControlCode',    'int16'),
        AVBPropertyDef('control_sub_code', 'OMFI:TRAK:ControlSubCode', 'int16'),
        AVBPropertyDef('lock_number',      'OMFI:TRAK:LockNubmer',     'int16'),

    ]
    def __init__(self, root):
        super(Track, self).__init__(root)
        self.refs = []

    @property
    def segment(self):
        for item in self.refs:
            obj = item.value
            if isinstance(obj, Component):
                return obj

@utils.register_class
class TrackGroup(Component):
    class_id = b'TRKG'
    propertydefs = Component.propertydefs + [
        AVBPropertyDef('mc_mode',     'OMFI:TRKG:MC:Mode',     'int8'),
        AVBPropertyDef('length',      'OMFI:TRKG:GroupLength',  'int32'),
        AVBPropertyDef('num_scalars', 'OMFI:TRKG:NumScalars',  'int32'),
        AVBPropertyDef('tracks',      'OMFI:TRKG:Tracks',      'list')
    ]

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
            track = Track(self.root)
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

            # TODO: find sample?
            elif track.flags in (543,):
                ref_count = 5
            else:
                raise ValueError("%s: unknown track flag %d" % (str(self.class_id), track.flags))



            for j in range(ref_count):
                ref = read_object_ref(self.root, f)
                track.refs.append(ref)

            if ref_count == 5:
                print(track.refs)
                raise Exception()

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
    propertydefs = TrackGroup.propertydefs + [
        AVBPropertyDef('left_length',         'OMFI:TKFX:MC:LeftLength',            'int32'),
        AVBPropertyDef('right_length',        'OMFI:TKFX:MC:RightLength',           'int32'),
        AVBPropertyDef('info_version',        'OMFI:TNFX:MC:GlobalInfoVersion',     'int16'),
        AVBPropertyDef('info_current',        'OMFI:TNFX:MC:GlobalInfo.kfCurrent',  'int32'),
        AVBPropertyDef('info_smooth',         'OMFI:TNFX:MC:GlobalInfo.kfSmooth',   'int32'),
        AVBPropertyDef('info_color_item',     'OMFI:TNFX:MC:GlobalInfo.colorItem',  'int16'),
        AVBPropertyDef('info_quality',        'OMFI:TNFX:MC:GlobalInfo.quality',    'int16'),
        AVBPropertyDef('info_is_reversed',    'OMFI:TNFX:MC:GlobalInfo.isReversed', 'int8'),
        AVBPropertyDef('info_aspect_on',      'OMFI:TNFX:MC:GlobalInfo.aspectOn',   'bool'),
        AVBPropertyDef('info_force_software', 'OMFI:TNFX:MC:ForceSoftware',         'bool'),
        AVBPropertyDef('info_never_hardware', 'OMFI:TKFX:MC:NeverHardware',         'bool'),
        AVBPropertyDef('trackman',            'OMFI:TKFX:MC:TrackMan',         'reference'),
    ]
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

        for tag in iter_ext(f):
            if tag == 0x02:
                read_assert_tag(f, 72)
                self.trackman = read_object_ref(self.root, f)
            else:
                raise ValueError("%s: unknown ext tag 0x%02X %d" % (str(self.class_id), tag,tag))

        if self.class_id is b'TKFX':
            tag = read_byte(f)
            assert tag == 0x03

@utils.register_class
class PanVolumeEffect(TrackEffect):
    class_id = b'PVOL'
    propertydefs = TrackEffect.propertydefs + [
        AVBPropertyDef('level',                  'OMFI:PVOL:MC:Level',               'int32'),
        AVBPropertyDef('pan',                    'OMFI:PVOL:MC:Pan',                 'int32'),
        AVBPropertyDef('suppress_validation',    'OMFI:PVOL:MC:SuppressValidation',  'bool'),
        AVBPropertyDef('level_set',              'OMFI:PVOL:MC:LevelSet',            'bool'),
        AVBPropertyDef('pan_set',                'OMFI:PVOL:MC:PanSet',              'bool'),
        AVBPropertyDef('supports_seperate_gain', 'OMFI:PVOL:MC:DoesSuprtSeprtClipG', 'int32'),
        AVBPropertyDef('is_trim_gain_effect',    'OMFI:PVOL:MC:IsTrimGainEffect',    'int32'),
    ]
    def read(self, f):
        super(PanVolumeEffect, self).read(f)

        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x05

        self.level = read_s32le(f)
        self.pan = read_s32le(f)

        self.suppress_validation = read_bool(f)
        self.level_set = read_bool(f)
        self.pan_set = read_bool(f)

        for tag in iter_ext(f):
            if tag == 0x01:
                read_assert_tag(f, 71)
                self.supports_seperate_gain = read_s32le(f)
            elif tag == 0x02:
                read_assert_tag(f, 71)
                self.is_trim_gain_effect = read_s32le(f)
            else:
                raise ValueError("%s: unknown ext tag 0x%02X %d" % (str(self.class_id), tag,tag))

        tag = read_byte(f)
        assert tag == 0x03

class ASPIPlugin(core.AVBObject):
    propertydefs = [
        AVBPropertyDef('name',             'OMFI:ASPI:plugInName',             'string'),
        AVBPropertyDef('manufacturer_id',  'OMFI:ASPI:plugInfManufacturerID',  'uint32'),
        AVBPropertyDef('product_id',       'OMFI:ASPI:plugInfProductID',       'uint32'),
        AVBPropertyDef('plugin_id',        'OMFI:ASPI:plugInfPlugInID',        'uint32'),
        AVBPropertyDef('chunks',           'OMFI:ASPI:plugInChunks',           'list'),
    ]

    def __init__(self, root):
        super(ASPIPlugin, self).__init__(root)
        self.chunks = []

class ASPIPluginChunk(core.AVBObject):
    propertydefs = [
        AVBPropertyDef('version',         'OMFI:ASPI:chunkfVersion',         'int32'),
        AVBPropertyDef('manufacturer_id', 'OMFI:ASPI:plugInfManufacturerID', 'uint32'),
        AVBPropertyDef('product_id',      'OMFI:ASPI:plugInfProductID',      'uint32'),
        AVBPropertyDef('plugin_id',       'OMFI:ASPI:plugInfPlugInID',       'uint32'),
        AVBPropertyDef('chunk_id',        'OMFI:ASPI:chunkfChunkID',         'uint32'),
        AVBPropertyDef('name',            'OMFI:ASPI:chunkfChunkName',       'string'),
        AVBPropertyDef('data',            'OMFI:ASPI:chunkfData',            'bytes'),
    ]

@utils.register_class
class AudioSuitePluginEffect(TrackEffect):
    class_id = b'ASPI'
    propertydefs = TrackEffect.propertydefs + [
        AVBPropertyDef('plugins',          'OMFI:ASPI:plugIns',                         'list'),
        AVBPropertyDef('mob_id',           'MobID',                                     'MobID'),
        AVBPropertyDef('mark_in',          'OMFI:ASPI:markInForSourceMasterClip',       'uint64'),
        AVBPropertyDef('mark_out',         'OMFI:ASPI:markOutForSourceMasterClip',      'uint64'),
        AVBPropertyDef('tracks_to_affect', 'OMFI:ASPI:tracksToAffect',                  'uint32'),
        AVBPropertyDef('rendering_mode',   'OMFI:ASPI:renderingMode',                   'int32'),
        AVBPropertyDef('padding_secs',     'OMFI:ASPI:paddingSecs',                     'int32'),
        AVBPropertyDef('preset_path',      'OMFI:ASPI:presetPath',                      'bytes'),
    ]
    def read(self, f):
        super(AudioSuitePluginEffect, self).read(f)

        read_assert_tag(f, 0x02)
        read_assert_tag(f, 0x01)

        self.plugins = []

        number_of_plugins = read_s32le(f)

        #TODO: find sample with multiple plugins
        assert number_of_plugins == 1

        plugin = ASPIPlugin(self.root)
        plugin.name = read_string(f)
        plugin.manufacturer_id = read_u32le(f)
        plugin.product_id = read_u32le(f)
        plugin.plugin_id = read_u32le(f)

        num_of_chunks = read_s32le(f)

        #TODO: find sample with multiple chunks
        assert num_of_chunks == 1

        chunk_size = read_s32le(f)
        assert chunk_size >= 0

        chunk = ASPIPluginChunk(self.root)
        chunk.version = read_s32le(f)
        chunk.manufacturer_id = read_u32le(f)
        chunk.roduct_id = read_u32le(f)
        chunk.plugin_id = read_u32le(f)

        chunk.chunk_id = read_u32le(f)
        chunk.name = read_string(f)

        chunk.data = bytearray(f.read(chunk_size))

        plugin.chunks.append(chunk)
        self.plugins.append(plugin)

        # print(peek_data(f).encode("hex"))


        for tag in iter_ext(f):
            if tag == 0x01:
                # not sure what is used for. skiping
                read_assert_tag(f, 71)
                mob_hi = read_s32le(f)
                read_assert_tag(f, 71)
                mob_lo = read_s32le(f)
            elif tag == 0x02:
                read_assert_tag(f, 77)
                self.mark_in = read_s64le(f)
            elif tag == 0x03:
                read_assert_tag(f, 77)
                self.mark_out = read_s64le(f)
            elif tag == 0x04:
                read_assert_tag(f, 72)
                self.tracks_to_affect = read_s32le(f)
            elif tag == 0x05:
                read_assert_tag(f, 71)
                self.rendering_mode = read_s32le(f)
            elif tag == 0x06:
                read_assert_tag(f, 71)
                self.padding_secs = read_s32le(f)
            elif tag == 0x08:
                mob_id = mobid.MobID()
                read_assert_tag(f, 65)
                length = read_s32le(f)
                assert length == 12
                mob_id.SMPTELabel = [read_byte(f) for i in range(12)]
                read_assert_tag(f, 68)
                mob_id.length = read_byte(f)
                read_assert_tag(f, 68)
                mob_id.instanceHigh = read_byte(f)
                read_assert_tag(f, 68)
                mob_id.instanceMid = read_byte(f)
                read_assert_tag(f, 68)
                mob_id.instanceLow = read_byte(f)
                read_assert_tag(f, 72)
                mob_id.Data1 = read_u32le(f)
                read_assert_tag(f, 70)
                mob_id.Data2 = read_u16le(f)
                read_assert_tag(f, 70)
                mob_id.Data3 = read_u16le(f)
                read_assert_tag(f, 65)
                length = read_s32le(f)
                assert length == 8
                mob_id.Data4 = [read_byte(f) for i in range(8)]
                self.mob_id = mob_id

            elif tag == 0x09:
                read_assert_tag(f, 72)
                preset_path_length = read_u32le(f)
                read_assert_tag(f, 65)
                length = read_u32le(f)
                assert preset_path_length == length
                self.preset_path = bytearray(f.read(length))
            else:
                raise ValueError("%s: unknown ext tag 0x%02X %d" % (str(self.class_id), tag,tag))

        read_assert_tag(f, 0x03)

class EqualizerBand(core.AVBObject):
    propertydefs = [
        AVBPropertyDef('type',   'OMFI:EQBD:AV:BandType',   'int32'),
        AVBPropertyDef('freq',   'OMFI:EQBD:AV:BandFreq',   'int32'),
        AVBPropertyDef('gain',   'OMFI:EQBD:AV:BandGain',   'int32'),
        AVBPropertyDef('q',      'OMFI:EQBD:AV:BandQ',      'int32'),
        AVBPropertyDef('enable', 'OMFI:EQBD:AV:BandEnable', 'bool'),
    ]

@utils.register_class
class EqualizerMultiBand(TrackEffect):
    class_id = b'EQMB'
    propertydefs = TrackEffect.propertydefs + [
        AVBPropertyDef('bands',         'OMFI:EQBD:AV:Bands',        'list'),
        AVBPropertyDef('effect_enable', 'OMFI:EQMB:AV:EffectEnable', 'bool'),
        AVBPropertyDef('filter_name',   'OMFI:EQMB:AV:FilterName',   'string'),
    ]

    def read(self, f):
        super(EqualizerMultiBand, self).read(f)
        # print(peek_data(f).encode("hex"))

        read_assert_tag(f, 0x02)
        read_assert_tag(f, 0x05)

        num_bands = read_s32le(f)
        assert num_bands >= 0

        self.bands = []
        for i in range(num_bands):
            band = EqualizerBand(self.root)
            band.type = read_s32le(f)
            band.freq = read_s32le(f)
            band.gain = read_s32le(f)
            band.q = read_s32le(f)
            band.enable = read_bool(f)
            self.bands.append(band)

        self.effect_enable = read_bool(f)
        self.filter_name = read_string(f)

        read_assert_tag(f, 0x03)

class TimeWarp(TrackGroup):
    class_id = b'WARP'
    propertydefs = TrackGroup.propertydefs + [
        AVBPropertyDef('phase_offset', 'OMFI:WARP:PhaseOffset', 'int32'),
    ]

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
    propertydefs = TimeWarp.propertydefs + [
        AVBPropertyDef('is_double', 'OMFI:MASK:IsDouble', 'bool'),
        AVBPropertyDef('mask_bits', 'OMFI:MASK:MaskBits', 'int32'),
    ]
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
    propertydefs = TimeWarp.propertydefs + [
        AVBPropertyDef('rate',                   'OMFI:SPED:Rate',                 'rational'),
        AVBPropertyDef('offset_adjust',          'OMIF:SPED:OffsetAdjust',         'double'),
        AVBPropertyDef('source_param_list',      'OMFI:SPED:SourceParamList',      'reference'),
        AVBPropertyDef('new_source_calculation', 'OMIF:SPED:NewSourceCalculation', 'bool'),
    ]
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

        for tag in iter_ext(f):

            if tag == 0x01:
                read_assert_tag(f, 75)
                self.offset_adjust = read_doublele(f)
            elif tag == 0x02:
                read_assert_tag(f, 72)
                self.source_param_list = read_object_ref(self.root, f)
            elif tag == 0x03:
                read_assert_tag(f, 66)
                self.new_source_calculation = read_bool(f)
            else:
                raise ValueError("%s: unknown ext tag 0x%02X %d" % (str(self.class_id), tag,tag))

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
class RepSet(TrackGroup):
    class_id = b'RSET'
    propertydefs = TrackGroup.propertydefs + [
        AVBPropertyDef('rep_set_type', 'OMFI:RSET:repSetType', 'int32'),
    ]
    def read(self, f):
        super(RepSet, self).read(f)

        # print(peek_data(f).encode("hex"))
        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x01

        for tag in iter_ext(f):
            if tag == 0x01:
                read_assert_tag(f, 71)
                self.rep_set_type = read_s32le(f)
            else:
                raise ValueError("%s: unknown ext tag 0x%02X %d" % (str(self.class_id), tag,tag))

        tag = read_byte(f)
        assert tag == 0x03

@utils.register_class
class TransistionEffect(TrackGroup):
    class_id = b'TNFX'
    propertydefs = TrackGroup.propertydefs + [
        AVBPropertyDef('cutpoint',            'OMFI:TRAN:CutPoint',                   'int32'),
        AVBPropertyDef('left_length',         'OMFI:TNFX:MC:LeftLength',              'int32'),
        AVBPropertyDef('right_length',        'OMFI:TNFX:MC:RightLength',             'int32'),
        AVBPropertyDef('info_version',        'OMFI:TNFX:MC:GlobalInfoVersion',       'int16'),
        AVBPropertyDef('info_current',        'OMFI:TNFX:MC:GlobalInfo.kfCurrent',    'int32'),
        AVBPropertyDef('info_smooth',         'OMFI:TNFX:MC:GlobalInfo.kfSmooth',     'int32'),
        AVBPropertyDef('info_color_item',     'OMFI:TNFX:MC:GlobalInfo.colorItem',    'int16'),
        AVBPropertyDef('info_quality',        'OMFI:TNFX:MC:GlobalInfo.quality',      'int16'),
        AVBPropertyDef('info_is_reversed',    'OMFI:TNFX:MC:GlobalInfo.isReversed',   'int8'),
        AVBPropertyDef('info_aspect_on',      'OMFI:TNTNFXFX:MC:GlobalInfo.aspectOn', 'bool'),
        AVBPropertyDef('info_force_software', 'OMFI:TNFX:MC:ForceSoftware',           'bool'),
        AVBPropertyDef('info_never_hardware', 'OMFI:TNFX:MC:NeverHardware',           'bool'),
        AVBPropertyDef('trackman',            'OMFI:TNFX:MC:TrackMan',           'reference'),
    ]
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

        for tag in iter_ext(f):
            if tag == 0x01:
                read_assert_tag(f, 72)
                self.trackman = read_object_ref(self.root, f)
            else:
                raise ValueError("%s: unknown ext tag 0x%02X %d" % (str(self.class_id), tag,tag))

        tag = read_byte(f)
        assert tag == 0x03

@utils.register_class
class Selector(TrackGroup):
    class_id = b'SLCT'
    propertydefs = TrackGroup.propertydefs + [
        AVBPropertyDef('is_ganged', 'OMFI:SLCT:IsGanged',      'bool'),
        AVBPropertyDef('selected',  'OMFI:SLCT:SelectedTrack', 'int16'),
    ]

    def read(self, f):
        super(Selector, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)

        assert tag == 0x02
        assert version == 0x01

        self.is_ganged = read_bool(f)
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
    propertydefs = TrackGroup.propertydefs + [
        AVBPropertyDef('last_modified', 'OMFI:MOBJ:LastModified',  'int32'),
        AVBPropertyDef('mob_type_id',   '__OMFI:MOBJ:MobType',     'int8'),
        AVBPropertyDef('usage_code',    'OMFI:MOBJ:UsageCode',     'int8'),
        AVBPropertyDef('descriptor',    'OMFI:MOBJ:PhysicalMedia', 'reference'),
        AVBPropertyDef('creation_time', 'OMFI:MOBJ:_CreationTime', 'int32'),
        AVBPropertyDef('mob_id',        'MobID',                   'MobID'),
    ]

    def read(self, f):
        super(Composition, self).read(f)
        tag = read_byte(f)
        version = read_byte(f)
        assert tag == 0x02
        assert version == 0x02

        mob_id_hi = read_s32le(f)
        mob_id_lo = read_s32le(f)
        self.last_modified = read_s32le(f)

        self.mob_type_id = read_byte(f)
        self.usage_code =  read_s32le(f)
        self.descriptor = read_object_ref(self.root, f)

        self.creation_time = None
        self.mob_id = None

        for tag in iter_ext(f):

            if tag == 0x01:
                read_assert_tag(f, 71)
                self.creation_time = read_datetime(f)
                self.mob_id = mobid.read_mob_id(f)
            else:
                raise ValueError("%s: unknown ext tag 0x%02X %d" % (str(self.class_id), tag,tag))

        read_assert_tag(f, 0x03)

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
