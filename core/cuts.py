# returns the value to sort shots by: first frame, then name when two shots start together
def shot_sort_key(shot):
    return (shot["frame_start"], shot["name"])


# decides where each camera cut starts and ends
# a cut starts where its shot starts and holds until the next shot starts
# the first cut starts at the scene start, the last cut holds to the scene end
def build_cut_list(manifest_data):
    scene = manifest_data["scene"]
    shots = sorted(manifest_data["shots"], key=shot_sort_key)

    cut_list = []
    for index in range(len(shots)):
        shot = shots[index]

        if index == 0:
            cut_start = scene["frame_start"]
        else:
            cut_start = shot["frame_start"]

        if index == len(shots) - 1:
            cut_end = scene["frame_end"]
        else:
            cut_end = shots[index + 1]["frame_start"] - 1

        # two shots with the same start, or a shot after the scene end, get no screen time
        if cut_end < cut_start:
            continue

        cut = {
            "shot": shot["name"],
            "frame_start": cut_start,
            "frame_end": cut_end,
        }
        cut_list.append(cut)
    return cut_list
