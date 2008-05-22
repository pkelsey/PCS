# Copyright (c) 2008, Bruce M. Simpson.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# Neither the name of the author nor the names of other
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# File: $Id$
#
# Author: Bruce M. Simpson
#
# Description: Classes which describe BSD routing socket messages.
#

import inspect
import struct
import time

import pcs
import payload
#from socket import AF_INET, inet_ntop, inet_ntoa

# TODO: bprintf-style flag printer.
# TODO: Add __str__ and __repr__ methods to objects which contain
# structured addresses.
# TODO: Deal with BSD routing socket address padding. These are handled
# in a very specific way.
# TODO: Deal with structure padding and architecture specific fields
# correctly.
# TODO: Test all this.

#
# Current FreeBSD routing socket version.
#
RTM_VERSION = 5

#
# Route flags
#
RTF_UP = 0x1			# route usable
RTF_GATEWAY = 0x2		# destination is a gateway
RTF_HOST = 0x4			# host entry (net otherwise)
RTF_REJECT = 0x8		# host or net unreachable
RTF_DYNAMIC = 0x10		# created dynamically (by redirect)
RTF_MODIFIED = 0x20		# modified dynamically (by redirect)
RTF_DONE = 0x40			# message confirmed
RTF_CLONING = 0x100		# generate new routes on use
RTF_XRESOLVE = 0x200		# external daemon resolves name
RTF_LLINFO = 0x400		# generated by link layer (e.g. ARP)
RTF_STATIC = 0x800		# manually added
RTF_BLACKHOLE = 0x1000		# just discard pkts (during updates)
RTF_PROTO2 = 0x4000		# protocol specific routing flag
RTF_PROTO1 = 0x8000		# protocol specific routing flag
RTF_PRCLONING = 0x10000		# unused, for compatibility
RTF_WASCLONED = 0x20000		# route generated through cloning
RTF_PROTO3 = 0x40000		# protocol specific routing flag
RTF_PINNED = 0x100000		# future use
RTF_LOCAL = 0x200000 		# route represents a local address
RTF_BROADCAST = 0x400000	# route represents a bcast address
RTF_MULTICAST = 0x800000	# route represents a mcast address

#
# Message types.
#
RTM_ADD = 0x1		# Add Route
RTM_DELETE = 0x2	# Delete Route
RTM_CHANGE = 0x3	# Change Metrics or flags
RTM_GET = 0x4		# Report Metrics
RTM_LOSING = 0x5	# Kernel Suspects Partitioning
RTM_REDIRECT = 0x6	# Told to use different route
RTM_MISS = 0x7		# Lookup failed on this address
RTM_LOCK = 0x8		# fix specified metrics
RTM_OLDADD = 0x9	# caused by SIOCADDRT
RTM_OLDDEL = 0xa	# caused by SIOCDELRT
RTM_RESOLVE = 0xb	# req to resolve dst to LL addr
RTM_NEWADDR = 0xc	# address being added to iface
RTM_DELADDR = 0xd	# address being removed from iface
RTM_IFINFO = 0xe	# iface going up/down etc.
RTM_NEWMADDR = 0xf	# mcast group membership being added to if
RTM_DELMADDR = 0x10	# mcast group membership being deleted
RTM_IFANNOUNCE = 0x11	# iface arrival/departure
RTM_IEEE80211 = 0x12	# IEEE80211 wireless event

#
# Bitmask values for rtm_inits and rmx_locks.
#
RTV_MTU = 0x1		# init or lock _mtu
RTV_HOPCOUNT = 0x2	# init or lock _hopcount
RTV_EXPIRE = 0x4	# init or lock _expire
RTV_RPIPE = 0x8		# init or lock _recvpipe
RTV_SPIPE = 0x10	# init or lock _sendpipe
RTV_SSTHRESH = 0x20	# init or lock _ssthresh
RTV_RTT = 0x40		# init or lock _rtt
RTV_RTTVAR = 0x80	# init or lock _rttvar

#
# Bitmask values for rtm_addrs.
#
RTA_DST = 0x1		# destination sockaddr present
RTA_GATEWAY = 0x2	# gateway sockaddr present
RTA_NETMASK = 0x4	# netmask sockaddr present
RTA_GENMASK = 0x8	# cloning mask sockaddr present
RTA_IFP = 0x10		# interface name sockaddr present
RTA_IFA = 0x20		# interface addr sockaddr present
RTA_AUTHOR = 0x40	# sockaddr for author of redirect
RTA_BRD = 0x80		# for NEWADDR, broadcast or p-p dest addr

#
# Index offsets for sockaddr array for alternate internal encoding.
#
RTAX_DST = 0		# destination sockaddr present
RTAX_GATEWAY = 1	# gateway sockaddr present
RTAX_NETMASK = 2	# netmask sockaddr present
RTAX_GENMASK = 3	# cloning mask sockaddr present
RTAX_IFP = 4		# interface name sockaddr present
RTAX_IFA = 5		# interface addr sockaddr present
RTAX_AUTHOR = 6		# sockaddr for author of redirect
RTAX_BRD = 7		# for NEWADDR, broadcast or p-p dest addr
RTAX_MAX = 8		# size of array to allocate

IFNAMSIZ = 16

IFAN_ARRIVAL = 0	# interface arrival
IFAN_DEPARTURE = 1	# interface departure

##
# * This macro returns the size of a struct sockaddr when passed
# * through a routing socket. Basically we round up sa_len to
# * a multiple of sizeof(long), with a minimum of sizeof(long).
# * The check for a NULL pointer is just a convenience, probably never used.
# * The case sa_len == 0 should only apply to empty structures.
#
# cdefine SA_SIZE(sa)						\
#    (  (!(sa) || ((struct sockaddr *)(sa))->sa_len == 0) ?	\
#	sizeof(long)		:				\
#	1 + ( (((struct sockaddr *)(sa))->sa_len - 1) | (sizeof(long) - 1) ) )
#

class if_link_msg(pcs.Packet):
    """BSD Routing socket -- link-state message (if_msghdr)"""

    _layout = pcs.Layout()
    _map = None
    _descr = None

    def __init__(self, bytes = None, timestamp = None, **kv):
        addrs = pcs.Field("addrs", 32)
        flags = pcs.Field("flags", 32)
        index = pcs.Field("index", 16)
        pad00 = pcs.Field("pad00", 16)		# XXX very likely it's padded
        # XXX We don't decode if_data yet.
        # Its length (and widths) are arch-dependent!
        data = pcs.Field("data", 152 * 8)

        pcs.Packet.__init__(self, [addrs, flags, index, pad00, ifdata], \
                            bytes = bytes, **kv)
        self.description = inspect.getdoc(self)

        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp

        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

class if_addr_msg(pcs.Packet):
    """BSD Routing socket -- protocol address message (ifa_msghdr) """

    _layout = pcs.Layout()
    _map = None
    _descr = None

    def __init__(self, bytes = None, timestamp = None, **kv):
        addrs = pcs.Field("addrs", 32)
        flags = pcs.Field("flags", 32)
        index = pcs.Field("index", 16)
        pad00 = pcs.Field("pad00", 16)		# XXX very likely it's padded
        metric = pcs.Field("metric", 32)

        pcs.Packet.__init__(self, [addrs, flags, index, pad00, metric], \
                            bytes = bytes, **kv)
        self.description = inspect.getdoc(self)

        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp

        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

class if_maddr_msg(pcs.Packet):
    """BSD Routing socket -- multicast group message (ifma_msghdr) """

    _layout = pcs.Layout()
    _map = None
    _descr = None

    def __init__(self, bytes = None, timestamp = None, **kv):
        addrs = pcs.Field("addrs", 32)
        flags = pcs.Field("flags", 32)
        index = pcs.Field("index", 16)

        pcs.Packet.__init__(self, [addrs, flags, index], bytes = bytes, **kv)
        self.description = inspect.getdoc(self)

        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp

        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

class if_state_msg(pcs.Packet):
    """BSD Routing socket -- interface-state message (if_announcemsghdr)"""

    _layout = pcs.Layout()
    _map = None
    _descr = None

    def __init__(self, bytes = None, timestamp = None, **kv):
        index = pcs.Field("index", 16)
        name = pcs.StringField("name", IFNAMSIZ * 8)
        what = pcs.Field("what", 16)

        pcs.Packet.__init__(self, [index, name, what], bytes = bytes, **kv)
        self.description = inspect.getdoc(self)

        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp

        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

#
# IEEE 802.11 support
#

class ieee80211_join_event(pcs.Packet):
    """BSD Routing socket -- IEEE 802.11 join event"""
    _layout = pcs.Layout()
    _map = None
    _descr = None
    def __init__(self, bytes = None, timestamp = None, **kv):
        address = pcs.Field("address", 6 * 8)
        pcs.Packet.__init__(self, [address], bytes = bytes, **kv)
        self.description = inspect.getdoc(self)
        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp
        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

class ieee80211_leave_event(pcs.Packet):
    """BSD Routing socket -- IEEE 802.11 leave event"""
    _layout = pcs.Layout()
    _map = None
    _descr = None
    def __init__(self, bytes = None, timestamp = None, **kv):
        address = pcs.Field("address", 6 * 8)
        pcs.Packet.__init__(self, [address], bytes = bytes, **kv)
        self.description = inspect.getdoc(self)
        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp
        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

class ieee80211_replay_event(pcs.Packet):
    """BSD Routing socket -- IEEE 802.11 replay event"""
    _layout = pcs.Layout()
    _map = None
    _descr = None
    def __init__(self, bytes = None, timestamp = None, **kv):
        src = pcs.Field("src", 6 * 8)
        dst = pcs.Field("dst", 6 * 8)
        cipher = pcs.Field("cipher", 8)
        keyid = pcs.Field("keyid", 8)
        keyix = pcs.Field("keyrsc", 64)
        rsc = pcs.Field("rsc", 64)
        pcs.Packet.__init__(self, [src, dst, cipher, keyid, keyix, rsc], \
                            bytes = bytes, **kv)
        self.description = inspect.getdoc(self)
        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp
        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

class ieee80211_michael_event(pcs.Packet):
    """BSD Routing socket -- IEEE 802.11 MICHAEL failure event"""
    _layout = pcs.Layout()
    _map = None
    _descr = None
    def __init__(self, bytes = None, timestamp = None, **kv):
        src = pcs.Field("src", 6 * 8)
        dst = pcs.Field("dst", 6 * 8)
        cipher = pcs.Field("cipher", 8)
        keyix = pcs.Field("keyrsc", 64)
        pcs.Packet.__init__(self, [src, dst, cipher, keyix], \
                            bytes = bytes, **kv)
        self.description = inspect.getdoc(self)
        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp
        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

RTM_IEEE80211_ASSOC = 100	# station associate (bss mode)
RTM_IEEE80211_REASSOC = 101	# station re-associate (bss mode)
RTM_IEEE80211_DISASSOC = 102	# station disassociate (bss mode)
RTM_IEEE80211_JOIN = 103	# station join (ap mode)
RTM_IEEE80211_LEAVE = 104	# station leave (ap mode)
RTM_IEEE80211_SCAN = 105	# scan complete, results available
RTM_IEEE80211_REPLAY = 106	# sequence counter replay detected
RTM_IEEE80211_MICHAEL = 107	# Michael MIC failure detected
RTM_IEEE80211_REJOIN = 108	# station re-associate (ap mode)

ieee80211_map = {
	RTM_IEEE80211_ASSOC:	ieee80211_join_event,
	RTM_IEEE80211_REASSOC:	ieee80211_join_event,
	RTM_IEEE80211_DISASSOC:	ieee80211_leave_event,
	RTM_IEEE80211_JOIN:	ieee80211_join_event,
	RTM_IEEE80211_LEAVE:	ieee80211_leave_event,
	RTM_IEEE80211_SCAN:	payload.payload,	# should be empty
	RTM_IEEE80211_REPLAY:	ieee80211_replay_event,
	RTM_IEEE80211_MICHAEL:	ieee80211_michael_event,
	RTM_IEEE80211_REJOIN:	ieee80211_join_event
}

ieee80211_descr = {
	RTM_IEEE80211_ASSOC:	"Associate",
	RTM_IEEE80211_REASSOC:	"Reassociate",
	RTM_IEEE80211_DISASSOC:	"Disassociate",
	RTM_IEEE80211_JOIN:	"Join",
	RTM_IEEE80211_LEAVE:	"Leave",
	RTM_IEEE80211_SCAN:	"Scan Complete",
	RTM_IEEE80211_REPLAY:	"Replay Detected",
	RTM_IEEE80211_MICHAEL:	"MICHAEL Failure",
	RTM_IEEE80211_REJOIN:	"Rejoin"
}

class if_ieee80211_msg(pcs.Packet):
    """BSD Routing socket -- IEEE 802.11 state messages (if_announcemsghdr)"""

    _layout = pcs.Layout()
    _map = ieee80211_map
    _descr = ieee80211_descr

    def __init__(self, bytes = None, timestamp = None, **kv):
        index = pcs.Field("index", 16)
        name = pcs.StringField("name", IFNAMSIZ * 8)
        what = pcs.Field("what", 16, discriminator=True)

        pcs.Packet.__init__(self, [index, name, what], bytes = bytes, **kv)
        self.description = inspect.getdoc(self)

        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp

        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

    def rdiscriminate(self, packet, discfieldname = None, map = ieee80211_map):
        """Reverse-map an encapsulated packet back to a discriminator
           field value. Like next() only the first match is used."""
        return pcs.Packet.rdiscriminate(self, packet, "what", map)

#
# What "route -nv monitor" knows about.
#
class rt_msg(pcs.Packet):
    """BSD Routing socket -- routing message"""

    _layout = pcs.Layout()
    _map = None
    _descr = None

    def __init__(self, bytes = None, timestamp = None, **kv):
        """ Define the common rtmsg header; see <net/route.h>. """
        index = pcs.Field("index", 16)
        flags = pcs.Field("flags", 32)
        addrs = pcs.Field("addrs", 32)
        pid = pcs.Field("pid", 32)
        seq = pcs.Field("seq", 32)
        errno = pcs.Field("errno", 32)
        fmask = pcs.Field("fmask", 32)
        inits = pcs.Field("inits", 32)
        # 14 * sizeof(long) on platform; arch-specific.
        #rmx = pcs.Field("rmx", 32)

        pcs.Packet.__init__(self, [index, flags, addrs, pid, seq, errno, \
                                   fmask, inits], bytes = bytes, **kv)
        self.description = inspect.getdoc(self)

        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp

        if bytes is not None:
            offset = self.sizeof()
            self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

# What "route -nv monitor" knows about.
rtmsg_map = {
	# struct rtmsg_hdr
	RTM_ADD:			rt_msg,
	RTM_DELETE:			rt_msg,
	RTM_CHANGE:			rt_msg,
	RTM_GET:			rt_msg,
	RTM_LOSING:			rt_msg,
	RTM_REDIRECT:			rt_msg,
	RTM_MISS:			rt_msg,
	RTM_LOCK:			rt_msg,
	RTM_RESOLVE:			rt_msg,
	# struct if_msghdr
	RTM_IFINFO:			if_link_msg,
	# struct ifa_msghdr
	RTM_NEWADDR:			if_addr_msg,
	RTM_DELADDR:			if_addr_msg,
	# struct ifma_msghdr
	RTM_NEWMADDR:			if_maddr_msg,
	RTM_DELMADDR:			if_maddr_msg,
	# struct if_announcemsghdr
	RTM_IFANNOUNCE:			if_state_msg,
	# struct if_announcemsghdr ('what' overloaded)
	RTM_IEEE80211:			if_ieee80211_msg
}

descr = {
	RTM_ADD:			"Added route",
	RTM_DELETE:			"Deleted route",
	RTM_CHANGE:			"Changed metrics or flags",
	RTM_GET:			"Report metrics",
	RTM_LOSING:			"Kernel suspects partitioning",
	RTM_REDIRECT:			"Redirected",
	RTM_MISS:			"Lookup failed",
	RTM_LOCK:			"Fix metrics",
	RTM_RESOLVE:			"Route cloned",
	RTM_IFINFO:			"Link-state change",
	RTM_NEWADDR:			"Added protocol address",
	RTM_DELADDR:			"Removed protocol address",
	RTM_NEWMADDR:			"Joined group",
	RTM_DELMADDR:			"Left group",
	RTM_IFANNOUNCE:			"Interface change",
	RTM_IEEE80211:			"IEEE 802.11 event"
}

class rtmsghdr(pcs.Packet):
    """BSD Routing socket -- message header (common to all messages)"""

    _layout = pcs.Layout()
    _map = rtmsg_map
    _descr = descr

    def __init__(self, bytes = None, timestamp = None, **kv):
        """ Define the common rtmsg header; see <net/route.h>. """
        msglen = pcs.Field("msglen", 16)
        version = pcs.Field("version", 8, default=RTM_VERSION)
        type = pcs.Field("type", 8, discriminator=True)
        # XXX There's implicit padding all over the shop here.
        pad0 = pcs.Field("type", 16)

        pcs.Packet.__init__(self, [msglen, version, type, pad0], \
                            bytes = bytes, **kv)
        self.description = inspect.getdoc(self)

        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp

        if bytes is not None:
            # XXX Workaround Packet.next() -- it only returns something
            # if it can discriminate.
            # XXX Should try rtmsg next, next.
            offset = self.sizeof()
            self.data = self.next(bytes[offset:len(bytes)],
                                      timestamp = timestamp)
            if self.data is None:
                self.data = payload.payload(bytes[offset:len(bytes)])
        else:
            self.data = None

    def rdiscriminate(self, packet, discfieldname = None, map = rtmsg_map):
        """Reverse-map an encapsulated packet back to a discriminator
           field value. Like next() only the first match is used."""
        return pcs.Packet.rdiscriminate(self, packet, "type", map)

    def __str__(self):
        """Walk the entire packet and pretty print the values of the fields."""
        retval = self._descr[self.type] + "\n"
        for field in self._layout:
            retval += "%s %s\n" % (field.name, field.value)
        return retval
