#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import argparse
import inspect
import json
import sys
from dataclasses import dataclass

@dataclass
class Tags:
	language: str
	title: str

@dataclass
class Stream:
	index: int
	codec_name: str
	codec_type: str
	channel_layout: str
	width: int
	height: int
	tags: Tags

	def map_type(self):
		if self.codec_type == "video":
			return "v"
		elif self.codec_type == "audio":
			return "a"
		elif self.codec_type == "subtitle":
			return "s"

	def display_tag(self):
		if self.codec_type == "video":
			return "VID"
		elif self.codec_type == "audio":
			return "AUD"
		elif self.codec_type == "subtitle":
			return "SUB"

	def __repr__(self):
		dt = self.display_tag()
		if self.codec_type == "video":
			return f"#{self.index} [{dt}] {self.tags.language}: \"{self.tags.title}\", {self.codec_name}, {self.width}×{self.height}"
		elif self.codec_type == "audio":
			return f"#{self.index} [{dt}] {self.tags.language}: \"{self.tags.title}\", {self.codec_name}, {self.channel_layout}"
		elif self.codec_type == "subtitle":
			return f"#{self.index} [{dt}] {self.tags.language}: \"{self.tags.title}\", {self.codec_name}"

	@classmethod
	def from_json(cls, j):
		index = j.get("index", -1)
		codec_name = j.get("codec_name", "N/A")
		codec_type = j.get("codec_type", "N/A")
		channel_layout = j.get("channel_layout", "N/A")
		width = j.get("width", -1)
		height = j.get("height", -1)
		if "tags" not in j:
			return cls(index, codec_name, codec_type, channel_layout, width, height, None)

		language = j["tags"].get("language", "N/A")
		title = j["tags"].get("title", "N/A")
		return cls(index, codec_name, codec_type, channel_layout, width, height, Tags(language, title))

def ffprobe(video):
	ffprobe_args = [
		"ffprobe", "-i", video,
		"-hide_banner",
		"-loglevel", "quiet",
		"-print_format", "json",
		"-show_streams",
		"-sexagesimal"
		# "-show_entries", "stream=width,height,duration,r_frame_rate"
	]

	p = subprocess.Popen(ffprobe_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

	ffprobe_output = p.stdout.read()
	ffprobe_json = json.loads(ffprobe_output)
	return ffprobe_json

def parse_file(in_file):
	f = ffprobe(in_file)
	if "streams" not in f:
		print("ffprobe error")

	return [Stream.from_json(s) for s in f["streams"]]

def list_streams(streams):
	for s in streams:
		print(s)

def process_file(video, remove_streams, out_file):
	ffmpeg_args = [
		"ffmpeg", "-i", video,
		"-hide_banner",
		"-v", "warning",
		"-y",
		"-map", "0"
	]

	for s in remove_streams:
		ffmpeg_args.extend(["-map", f"-0:{s.index}"])

	ffmpeg_args.extend(["-c", "copy", out_file])

	# print(" ".join(ffmpeg_args))
	p = subprocess.run(ffmpeg_args, stderr=sys.stderr, stdout=sys.stdout)

def main(args):
	streams = parse_file(args.i)

	if args.list:
		list_streams(streams)
		return

	if not args.out:
		print("You must specify an output file.")

	remove_streams = []
	for s in streams:
		if s.codec_type == "video":
			continue

		if args.keep:
			if s.tags.language not in args.keep:
				remove_streams.append(s)
		elif args.exclude:
			if s.tags.language in args.exclude:
				remove_streams.append(s)

	print("Removing these streams:")
	for s in remove_streams:
		print(s)

	process_file(args.i, remove_streams, args.out)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="MKV audio/subtitle remover")
	parser.add_argument("-i", metavar="input", type=str, required=True, help="Input file")
	parser.add_argument("-l", "--list", action="store_true", help="List streams")
	parser.add_argument("out", type=str, nargs="?", help="Output file")

	in_ex_group = parser.add_mutually_exclusive_group()
	in_ex_group.add_argument("-k", "--keep", type=str, action="append", help="Languages to keep")
	in_ex_group.add_argument("-x", "--exclude", type=str, action="append", help="Languages to exclude")

	args = parser.parse_args()
	main(args)