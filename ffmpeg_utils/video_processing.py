import json
import glob
import logging
import numpy as np
import os
import shlex
import tempfile
import time
import uuid
from datetime import timedelta, datetime
from subprocess import call, run, PIPE, STDOUT


def get_video_length(video_file_path):
    """
    This function computes the duration of the given video file.
    :return: (int) duration_in_seconds
    """
    try:
        result = run(
            [
                "/usr/bin/ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_file_path,
            ],
            stdout=PIPE,
            stderr=STDOUT,
        )
        duration_secs = result.stdout
        if type(duration_secs) == str:
            duration_secs = duration_secs.split(".")
        else:
            duration_secs = duration_secs.decode("utf-8").split(".")
        return int(duration_secs[0])
    except:
        return 0


def merge_video_with_diff_fps(file_names_list, ts_id=None, debug=True, final_video_path="", no_audio=False):
    st = time.time()
    if final_video_path == "":
        video_path = os.path.dirname(file_names_list[0])
        final_video_path = video_path + "/" + str(uuid.uuid4()) + ".mp4"
    # Considering videos are already sorted
    # file_names_list.sort(key=lambda x: int(x.split("/")[-1].split('_')[0]))
    # print(file_names_list)
    a_str = ""
    for i in file_names_list:
        a_str += "-i " + i + " "

    if debug:
        logging.info(
            "TestSession: {0} | Total videos {1} String length {2}.".format(ts_id, len(file_names_list), len(a_str))
        )
    if no_audio:
        cmd = ("ffmpeg -loglevel panic {0} -filter_complex '[0:v:0][1:v:0] concat=n={1}:v=1[outv]' -map '[outv]' "
               " -strict -2 {2}".format(a_str, len(file_names_list), final_video_path))
    else:
        cmd = (
            "ffmpeg -loglevel panic {0} -filter_complex '[0:v:0][0:a:0][1:v:0][1:a:0] concat=n={1}:v=1:a=1[outv][outa]' -map '[outv]' "
            "-map '[outa]' -strict -2 {2}".format(a_str, len(file_names_list), final_video_path)
        )
    ffmpeg_status = call(shlex.split(cmd), shell=False)
    if ffmpeg_status != 0:
        logging.exception("TestSession: {0} | error while merge_video_with_diff_fps video.".format(ts_id))

    if debug:
        logging.info(
            "TestSession: {0} | Time taken for merge_video_with_diff_fps is {1} secs for {2}.".format(
                ts_id, time.time() - st, no_audio)
        )

    return final_video_path, ffmpeg_status


def merge_videos_with_ts_method(file_names_list, ts_id=None, debug=True, final_video_path=""):
    concat_str = ""
    for video_file in file_names_list:
        # convert .mp4 files to .ts files, which is the required format of input files to be concatenated.
        filename = os.path.basename(video_file).replace("mp4", "ts")
        output_file = os.path.join(os.path.dirname(video_file), filename)
        cmd = "ffmpeg -loglevel panic -i {0} -y -c copy -bsf:v h264_mp4toannexb -f mpegts {1}".format(
            video_file, output_file
        )

        call(shlex.split(cmd), shell=False)

        concat_str += "|{0}".format(output_file)
    if file_names_list:
        if not final_video_path:
            final_video_path = os.path.join(os.path.dirname(file_names_list[0]), str(uuid.uuid4()) + "_merged_file.mp4")
        merge_cmd = 'ffmpeg -loglevel panic -i "concat:{0}" -y -c copy -bsf:a aac_adtstoasc {1}'.format(
            concat_str[1:], final_video_path)
        execution_status = call(shlex.split(merge_cmd), shell=False)
        if execution_status != 0:
            logging.exception("TestSession: {0} | error while merge_videos_with_ts_method video.".format(ts_id))
        ts_files = glob.glob(os.path.join(os.path.dirname(file_names_list[0]), '*.ts'))
        for video_file in ts_files:
            remove_dir_cmd = "rm -rf {}".format(video_file)
            call(shlex.split(remove_dir_cmd), shell=False)
    return final_video_path


def generate_preview_image_from_images(input_file_dir, preview_image_name):
    tile_width_img = 4
    tile_height_img = 2  # create 4x2 tile
    input_file_cmd = os.path.join(input_file_dir, "*.jpg")
    preview_img_command = 'ffmpeg -loglevel panic -pattern_type glob -i "{0}" ' \
                          '-filter_complex scale=iw/2:-1,tile={1}x{2} {3}'.format(input_file_cmd, tile_width_img,
                                                                                  tile_height_img, preview_image_name)
    # check the image file name and end-time - start-time
    call(shlex.split(preview_img_command), shell=False)
    if os.path.exists(preview_image_name):
        return preview_image_name  # return image path if it exists
    else:
        return False


def generate_preview_image(video_file_path, start_time, end_time, preview_image_name):
    if start_time < 0:
        start_time = 0
    tile_width_img = 4
    tile_height_img = 2  # create 4x2 tile
    num_frames_to_tile = tile_width_img * tile_height_img
    if end_time - start_time < num_frames_to_tile:  # if too short duration
        end_time = start_time + num_frames_to_tile
    frame_rate = float(num_frames_to_tile) / (end_time - start_time)
    preview_img_command = "ffmpeg -loglevel panic -i {0} -frames 1 -q:v 1 -vf {1} select='between(t\,{2}\,{3})'," \
                          "fps={4},scale=iw/2:-1,tile={5}x{6}:margin=2:padding=2{7} -y {8}".format(video_file_path,
                                                                                                   "\"",
                                                                                                   start_time,
                                                                                                   end_time,
                                                                                                   frame_rate,
                                                                                                   tile_width_img,
                                                                                                   tile_height_img,
                                                                                                   "\"",
                                                                                                   preview_image_name)
    # check the image file name and end-time - start-time
    call(shlex.split(preview_img_command), shell=False)
    if os.path.exists(preview_image_name):
        return preview_image_name  # return image path if it exists
    else:
        return False


def extract_frames_from_video(video_file_path, start_time, end_time, fps, extracted_frames_path):
    dir_cmd = 'mkdir -p {}'.format(extracted_frames_path)
    call(shlex.split(dir_cmd), shell=False)
    cmd = "ffmpeg -loglevel panic -i {0} -ss {1} -to {2} -r {3} {4}/%d.jpg".format(video_file_path, start_time,
                                                                                end_time, fps, extracted_frames_path)
    return call(shlex.split(cmd), shell=False)


def trim_video(video_file_path, start_time, end_time=None, trim_video_path='/tmp/trim_video.mp4'):
    if end_time is None:
        end_time = get_video_length(video_file_path)
    split_cmd = 'ffmpeg -loglevel panic -i {0} -ss {1} -t {2} {3}'.format(video_file_path, start_time,
                                                                          end_time - start_time, trim_video_path)
    return call(shlex.split(split_cmd), shell=False)


if __name__ == '__main__':
    videos = glob.glob('/home/prabodh/Downloads/videos/*')
    # merge_videos_with_ts_method(videos, final_video_path='/tmp/merged_with_ts.mp4')
    # merge_video_with_diff_fps(videos, final_video_path='/tmp/merged_with_diff_fps.mp4', no_audio=True)
    # generate_preview_image_from_images('/home/prabodh/personal_space/Video_Processing/sample_frames',
    #                                    'collage_from_images.jpg')
    # generate_preview_image('blurr_woman_practising_yoga.mp4', 2, 2 + 8, 'collage_from_video.jpg')
    # extract_frames_from_video('blurr_woman_practising_yoga.mp4', 2, 2 + 8, 1, 'sample_frames')
    trim_video('blurr_woman_practising_yoga.mp4', 8, trim_video_path='blurr_woman_practising_yoga-part-2.mp4')