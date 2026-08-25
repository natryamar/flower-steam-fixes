#!/usr/bin/env python3
"""Read-only SBlk metadata inspector for Flower's PC sound banks."""

from __future__ import annotations

import argparse
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, cast

AudioUser = tuple[int, str, int]


@dataclass(frozen=True)
class Grain:
    index: int
    ref: int
    packed: int
    grain_type: int
    payload_rel: int
    payload: int
    ref_aux: int
    target_rel: int | None = None
    target_size: int | None = None
    stream_name: str | None = None


@dataclass(frozen=True)
class Event:
    index: int
    name: str
    record: int
    raw: bytes
    grain_count: int
    grain_list_offset: int
    grains: list[Grain]


@dataclass
class Type1Block:
    size: int
    payloads: set[int] = field(default_factory=set)
    users: list[AudioUser] = field(default_factory=list)


class _Arguments(Protocol):
    bank: Path
    event: str
    audio_neighbors: int


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def cstring(data: bytes, offset: int) -> str:
    end = data.index(0, offset)
    return data[offset:end].decode("ascii", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("bank", type=Path)
    _ = parser.add_argument("--event", default="HayBailDone")
    _ = parser.add_argument("--audio-neighbors", type=int, default=4)
    args = cast(_Arguments, cast(object, parser.parse_args()))

    data = args.bank.read_bytes()
    version = u32(data, 0x00)
    region_count = u32(data, 0x04)
    metadata_offset = u32(data, 0x08)
    metadata_size = u32(data, 0x0C)
    audio_offset = u32(data, 0x10)
    audio_size = u64(data, 0x14)
    sblk = metadata_offset

    if data[sblk : sblk + 4] != b"SBlk":
        raise SystemExit("SBlk signature not found at metadata offset")

    event_table_rel = u32(data, sblk + 0x18)
    grain_refs_rel = u32(data, sblk + 0x1C)
    payloads_rel = u32(data, sblk + 0x2C)
    names_rel = u32(data, sblk + 0x30)
    event_count = u16(data, sblk + 0x38)
    grain_ref_count = u16(data, sblk + 0x3A)
    payload_count_hint = u16(data, sblk + 0x3C)

    print("Outer bank")
    print(f"  version={version} region_count={region_count}")
    print(f"  SBlk: file=0x{metadata_offset:X} size=0x{metadata_size:X}")
    print(f"  audio: file=0x{audio_offset:X} size=0x{audio_size:X}")
    print(f"SBlk v{u32(data, sblk + 4)}")
    print(
        f"  event table: +0x{event_table_rel:X}, count={event_count}, "
        + "record_size=0x24"
    )
    print(
        f"  grain refs:  +0x{grain_refs_rel:X}, count={grain_ref_count}, "
        + "record_size=8"
    )
    print(f"  payloads:    +0x{payloads_rel:X}, count_hint={payload_count_hint}")
    print(f"  names:       +0x{names_rel:X}")

    names_base = sblk + names_rel
    name_records_rel = u32(data, names_base + 8)
    strings_rel = u32(data, names_base + 0xC)
    name_records = names_base + name_records_rel
    strings = names_base + strings_rel

    event_names: dict[int, str] = {}
    name_record_offsets: dict[int, int] = {}
    for record_index in range(event_count):
        record = name_records + record_index * 0x10
        string_rel = u32(data, record)
        event_index = u32(data, record + 0xC)
        event_names[event_index] = cstring(data, strings + string_rel)
        name_record_offsets[event_index] = record

    payload_users: dict[int, list[AudioUser]] = defaultdict(list)
    type1_blocks: dict[int, Type1Block] = {}
    events: list[Event] = []

    event_table = sblk + event_table_rel
    grain_refs = sblk + grain_refs_rel
    payloads = sblk + payloads_rel
    for event_index in range(event_count):
        record = event_table + event_index * 0x24
        grain_count = data[record + 8]
        grain_list_offset = u32(data, record + 0xC)
        grains: list[Grain] = []
        for grain_index in range(grain_count):
            ref = grain_refs + grain_list_offset + grain_index * 8
            packed = u32(data, ref)
            grain_type = packed >> 24
            payload_rel = packed & 0xFFFFFF
            payload = payloads + payload_rel
            user = (event_index, event_names[event_index], grain_index)
            payload_users[payload_rel].append(user)

            target_rel: int | None = None
            target_size: int | None = None
            stream_name: str | None = None
            if grain_type in (1, 0x2D):
                target_rel = u32(data, payload + 0x44)
                target_size = u32(data, payload + 0x48)
                if grain_type == 1:
                    block = type1_blocks.setdefault(
                        target_rel,
                        Type1Block(size=target_size),
                    )
                    block.payloads.add(payload_rel)
                    block.users.append(user)
                else:
                    stream_name = cstring(data, audio_offset + target_rel)

            grains.append(
                Grain(
                    index=grain_index,
                    ref=ref,
                    packed=packed,
                    grain_type=grain_type,
                    payload_rel=payload_rel,
                    payload=payload,
                    ref_aux=u32(data, ref + 4),
                    target_rel=target_rel,
                    target_size=target_size,
                    stream_name=stream_name,
                )
            )
        events.append(
            Event(
                index=event_index,
                name=event_names[event_index],
                record=record,
                raw=data[record : record + 0x24],
                grain_count=grain_count,
                grain_list_offset=grain_list_offset,
                grains=grains,
            )
        )

    selected = [event for event in events if event.name == args.event]
    if not selected:
        raise SystemExit(f"Event not found: {args.event}")
    event = selected[0]
    name_record = name_record_offsets[event.index]
    string_rel = u32(data, name_record)
    print(f"\nEvent {event.name!r}")
    print(f"  event ordinal: 0x{event.index:X} ({event.index})")
    print(f"  name record: file 0x{name_record:X}, string_rel=0x{string_rel:X}")
    print(f"  event record: file 0x{event.record:X}")
    print(f"  raw: {event.raw.hex(' ')}")
    print(
        f"  grain count={event.grain_count} "
        + f"list_rel=0x{event.grain_list_offset:X}"
    )

    sorted_blocks = sorted(type1_blocks)
    block_ordinals = {offset: index for index, offset in enumerate(sorted_blocks)}
    selected_offsets: list[int] = []
    for grain in event.grains:
        line = f"  grain {grain.index}: ref file 0x{grain.ref:X}, "
        line += f"packed=0x{grain.packed:08X}, type=0x{grain.grain_type:02X}, "
        line += (
            f"payload=+0x{grain.payload_rel:X} (file 0x{grain.payload:X}), "
        )
        line += f"aux=0x{grain.ref_aux:08X}"
        if grain.grain_type == 1:
            target_rel = grain.target_rel
            target_size = grain.target_size
            if target_rel is None or target_size is None:
                raise RuntimeError("Type-1 grain is missing its audio target")
            selected_offsets.append(target_rel)
            line += f", audio_block={block_ordinals[target_rel]} "
            line += f"(+0x{target_rel:X}, file 0x{audio_offset + target_rel:X}, "
            line += f"size=0x{target_size:X})"
        elif grain.grain_type == 0x2D:
            target_rel = grain.target_rel
            stream_name = grain.stream_name
            if target_rel is None or stream_name is None:
                raise RuntimeError("Stream grain is missing its stream target")
            line += f", stream_string=+0x{target_rel:X} "
            line += f"(field file 0x{grain.payload + 0x44:X}), "
            line += f"name={stream_name!r}"
        print(line)

    if selected_offsets:
        lo = max(
            0,
            min(block_ordinals[offset] for offset in selected_offsets)
            - args.audio_neighbors,
        )
        hi = min(
            len(sorted_blocks),
            max(block_ordinals[offset] for offset in selected_offsets)
            + args.audio_neighbors
            + 1,
        )
        print("\nNearby unique type-1 audio blocks (ordinal is sorted by data offset):")
        for ordinal in range(lo, hi):
            offset = sorted_blocks[ordinal]
            info = type1_blocks[offset]
            marker = "*" if offset in selected_offsets else " "
            users = ", ".join(
                f"{name}[{grain_index}]" for _, name, grain_index in info.users
            )
            block_line = f" {marker} block {ordinal:3d}: +0x{offset:08X}, "
            block_line += f"file 0x{audio_offset + offset:08X}, "
            block_line += f"size=0x{info.size:X}, users={users}"
            print(block_line)


if __name__ == "__main__":
    main()
