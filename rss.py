import json
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
            if package["details"]["timestamp"] > threshold:
                yield package

    return sorted(
        find_recent_packages(),
        key=lambda x: x["details"]["timestamp"],
        reverse=True,
    )


def get_rss(channel_name, channeldata_fn, threshold_days):
    with open(channeldata_fn, "r") as fd:
        data = json.load(fd)

        packages = get_recent_packages(
            data, threshold_days
        )  # Tue, 10 Jun 2003 09:41:01 GMT
        iso822 = lambda ts: time.strftime("%a, %d %b %Y %T GMT", time.gmtime(ts))
        channel = {
            "title": f"anaconda.org/{channel_name}",
            "link": f"https://conda.anaconda.org/{channel_name}",
            "description": f"An anaconda.org community with {len(packages)} recent package updates.",
            "pubDate": iso822(time.time()),
            "lastBuildDate": iso822(time.time()),
        }
        items = [
            {
                # Example: "7zip 19.00 [osx-64, win-64]"
                "title": f"{name} {package['version']} [{', '.join(sorted(package['subdirs']))}]",
                "description": package.get("description", package.get("summary")),
                "link": package.get("doc_url"),  # URI - project or project docs
                "comments": package.get("dev_url"),  # URI
                "guid": package.get("source_url"),  # URI - download link
                "timestamp": package["timestamp"],  # used for sorting
                "pubDate": iso822(package["timestamp"]),
                "source": package.get("home"),  # URI
                "##other": package.get("license"),  # extensibility object
            }
            for name, package in [(p["name"], p["details"]) for p in packages]
        ]
        # Sort and prepare the items for rendering.
        items.sort(key=lambda x: x["timestamp"])
        for item in items:
            del item["timestamp"]
            empty_fields = [k for k, v in item.items() if not v]
            for k in empty_fields:
                del item[k]

        rss = dicttoxml(
            {
                "channel": channel,
                "item": items,
            },
            custom_root="rss",
            attr_type=False,
        )

        return (
            parseString(rss)
            .toprettyxml(indent="  ")
            .replace("<rss>", '<rss version="2.0">')
        )


if __name__ == "__main__":
    print(get_rss("conda-forge", "./cloned/conda-forge/channeldata.json", 0.1))
