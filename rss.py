import time
from xml.dom.minidom import parseString
from dicttoxml import dicttoxml


def get_recent_packages(channeldata, threshold_days):

    threshold = time.time() - threshold_days * 24 * 60 * 60

    def all_packages():
        for name, package in channeldata.get("packages", {}).items():
            yield {"name": name, "details": package}
        for name, package in channeldata.get("packages.conda", {}).items():
            yield {"name": name, "details": package}

    def find_recent_packages():
        for package in all_packages():
            if package["details"].get("timestamp", threshold) > threshold:
                yield package

    return sorted(
        find_recent_packages(),
        key=lambda x: x["details"]["timestamp"],
        reverse=True,
    )


def iso822(timestamp):
    return time.strftime("%a, %d %b %Y %T GMT", time.gmtime(timestamp))


def get_channel(channel_name, packages, threshold_days):
    return {
        "title": f"anaconda.org/{channel_name}",
        "link": f"https://conda.anaconda.org/{channel_name}",
        "description": f"An anaconda.org community with {len(packages)} package updates in the past {threshold_days} days.",
        "pubDate": iso822(time.time()),
        "lastBuildDate": iso822(time.time()),
    }


def get_title(name, version, subdirs):
    return f"{name} {version} [{', '.join(sorted({x for x in subdirs}))}]"


def get_items(packages):
    items = []
    for name, package in [(p["name"], p["details"]) for p in packages]:
        __ = lambda x: package.get(x)
        coalesce = lambda *args: [package[x] for x in args if __(x)][0]
        item = {
            # Example: "7zip 19.00 [osx-64, win-64]"
            "title": get_title(name, __("version"), __("subdirs")),
            "description": coalesce("description", "summary"),
            "link": __("doc_url"),  # URI - project or project docs
            "comments": __("dev_url"),  # URI
            "guid": __("source_url"),  # URI - download link
            "pubDate": iso822(__("timestamp")),
            "source": __("home"),  # URI
        }
        empty_fields = [k for k, v in item.items() if not v]
        for k in empty_fields:
            del item[k]
        items.append(item)
    return items


def get_rss(channel_name, channeldata, threshold_days):
    packages = get_recent_packages(channeldata, threshold_days)
    rss = parseString(
        dicttoxml(
            {
                "channel": get_channel(channel_name, packages, threshold_days),
                "item": get_items(packages),
            },
            custom_root="rss",
            attr_type=False,
        )
    )
    rss.firstChild.setAttribute("version", "2.0")
    return rss.toprettyxml(indent="    ")


if __name__ == "__main__":
    import sys
    import json

    channel, channeldata_fn, threshold_days = sys.argv[1:]
    with channeldata_fn as fd:
        print(get_rss(channel, json.load(fd), int(threshold_days)))
