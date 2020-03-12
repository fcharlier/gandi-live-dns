#!/usr/bin/env python
# encoding: utf-8
"""
Gandi v5 LiveDNS - DynDNS Update via REST API and CURL/requests

@author: cave
@author: François Charlier <fcharlier@ploup.net>
License GPLv3
https://www.gnu.org/licenses/gpl-3.0.html

Created on 13 Aug 2017
Last update on 9 Sep 2019
http://doc.livedns.gandi.net/
http://doc.livedns.gandi.net/#api-endpoint -> https://dns.gandi.net/api/v5/
"""

import argparse
import config
import requests
import urllib3


session = requests.Session()
retry = urllib3.util.Retry(
    total=5,
    connect=5,
    read=5,
    status=5,
    status_forcelist=(403, 500, 502, 503),
    backoff_factor=1,
)
retry_adapter = requests.adapters.HTTPAdapter(max_retries=retry)
session.mount("https://", retry_adapter)
session.mount("http://", retry_adapter)


def get_dynip(ifconfig_provider):
    """ find out own IPv4 at home <-- this is the dynamic IP which changes more or less
    frequently similar to curl ifconfig.me/ip, see example.config.py for details to
    ifconfig providers
    """
    r = session.get(ifconfig_provider)
    # print('Checking dynamic IP: ' , r._content.strip('\n'))
    return r.text.strip("\n")


def get_uuid():
    """
    find out ZONE UUID from domain
    Info on domain "DOMAIN"
    GET /domains/<DOMAIN>:

    """
    url = config.api_endpoint + "/domains/" + config.domain
    u = session.get(url, headers={"X-Api-Key": config.api_secret})
    if u.status_code == 200:
        return u.json()["zone_uuid"]
    else:
        print("Error: HTTP Status Code ", u.status_code, "when trying to get Zone UUID")
        try:
            print(u.json()["message"])
        except ValueError:
            pass
        exit()


def get_dnsip(uuid):
    """ find out IP from first Subdomain DNS-Record
    List all records with name "NAME" and type "TYPE" in the zone UUID
    GET /zones/<UUID>/records/<NAME>/<TYPE>:

    The first subdomain from config.subdomain will be used to get
    the actual DNS Record IP
    """

    url = (
        config.api_endpoint
        + "/zones/"
        + uuid
        + "/records/"
        + config.subdomains[0]
        + "/A"
    )
    headers = {"X-Api-Key": config.api_secret}
    u = session.get(url, headers=headers)
    if u.status_code == 200:
        # print(
        #     "Checking IP from DNS Record",
        #     config.subdomains[0],
        #     ":",
        #     u.json()["rrset_values"][0].strip("\n"),
        # )
        return u.json()["rrset_values"][0].strip("\n")
    else:
        print(
            "Error: HTTP Status Code ",
            u.status_code,
            "when trying to get IP from subdomain",
            config.subdomains[0],
        )
        try:
            print(u.json()["message"])
        except ValueError:
            pass
        exit()


def update_records(uuid, dynIP, subdomain):
    """ update DNS Records for Subdomains
        Change the "NAME"/"TYPE" record from the zone UUID
        PUT /zones/<UUID>/records/<NAME>/<TYPE>:
        curl -X PUT -H "Content-Type: application/json" \
                    -H 'X-Api-Key: XXX' \
                    -d '{"rrset_ttl": 10800,
                         "rrset_values": ["<VALUE>"]}' \
                    https://dns.gandi.net/api/v5/zones/<UUID>/records/<NAME>/<TYPE>
    """
    url = config.api_endpoint + "/zones/" + uuid + "/records/" + subdomain + "/A"
    payload = {"rrset_ttl": config.ttl, "rrset_values": [dynIP]}
    headers = {"Content-Type": "application/json", "X-Api-Key": config.api_secret}
    u = session.put(url, json=payload, headers=headers)

    if u.status_code == 201:
        print(
            "Status Code:",
            u.status_code,
            ",",
            u.json()["message"],
            ", IP updated for",
            subdomain,
        )
        return True
    else:
        print(
            "Error: HTTP Status Code ",
            u.status_code,
            "when trying to update IP from subdomain",
            subdomain,
        )
        try:
            print(u.json()["message"])
        except ValueError:
            pass
        exit()


def main(force_update, verbosity):

    if verbosity:
        print("verbosity turned on - not implemented by now")

    # get zone ID from Account
    uuid = get_uuid()

    # compare dynIP and DNS IP
    dynIP = get_dynip(config.ifconfig)
    dnsIP = get_dnsip(uuid)

    if force_update:
        print("Going to update/create the DNS Records for the subdomains")
        for sub in config.subdomains:
            update_records(uuid, dynIP, sub)
    else:
        if dynIP == dnsIP:
            pass
            # print("IP Address Match - no further action")
        else:
            print(
                "IP Address Mismatch - "
                "going to update the DNS Records for "
                "the subdomains with new IP",
                dynIP,
            )
            for sub in config.subdomains:
                update_records(uuid, dynIP, sub)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "-f", "--force", help="force an update/create", action="store_true"
    )
    args = parser.parse_args()

    main(args.force, args.verbose)
