# coding=utf-8

import asyncio
import requests
import re

import config
import logging
logger = logging.getLogger('monitor')

class MsgHandler:
    def __init__(self, wx, robot):
        self.wx = wx
        self.robot = robot

    async def __parsemsg(self):
        msg = await self.wx.recvqueue.get()
        # 自己从别的平台发的消息忽略
        if msg['FromUserName'] == self.wx.My['UserName']:
            return None
        # 排除不是发给自己的消息
        if msg['ToUserName'] != self.wx.My['UserName']:
            return None
        # 在黑名单里面
        if msg['FromUserName'] in self.wx.blacklist:
            return None

        msginfo = {}
        # 文字消息
        if msg['MsgType'] == 1:
            content = msg['Content']
            fromsomeone_NickName = ''
            ## 来自群消息
            if msg['FromUserName'].find('@@') != -1:
                fromsomeone = content[:content.find(':<br/>')]
                groupname = msg['FromUserName']
                if groupname not in self.wx.grouplist:
                    await self.wx.updatequeue.put(groupname)
                elif fromsomeone in self.wx.grouplist[groupname]:
                    fromsomeone_NickName = self.wx.grouplist[groupname][fromsomeone]
                    fromsomeone_NickName = '@' + fromsomeone_NickName + ' '
                else:
                    await self.wx.updatequeue.put(groupname)
                await asyncio.sleep(0.5)
                if groupname in self.wx.grouplist:
                     msginfo['group_NickName'] = self.wx.grouplist[groupname]['NickName']

                # 去掉消息头部的来源信息
                content = content[content.find('>')+1:]
            # 普通消息
            else:
                fromsomeone_NickName = ''

            # print (content)
            if len(content)>1:
                regx = re.compile(r'@.+?\u2005')
                content = regx.sub(' ', content)

            msginfo['Content'] = content
            msginfo['fromsomeone'] = fromsomeone_NickName
            msginfo['FromUserName'] = msg['FromUserName']
            msginfo['MsgType'] = msg['MsgType']

            return msginfo
        else:
            return None

    async def msgloop(self):
        while True:
            msginfo = await self.__parsemsg()
            if msginfo != None:
                response = {}
                answer= await self.deal_pic_msg(msginfo)
                if answer:
                    response['Content'] = msginfo['fromsomeone'] + answer
                    response['user'] = msginfo['FromUserName']
                    response['MsgType'] = 1
                    await self.wx.sendqueue.put(response)
                    logger.info(msginfo['fromsomeone'] + ' say: ' + msginfo['Content'])
                    logger.info('Harry Potter say: ' + response['Content'])

            await asyncio.sleep(config.msgloop_interval)

    async def deal_pic_msg(self, msginfo):
        import pathlib
        if not pathlib.Path('tmp.png').exists():
            return
        logger.debug(msginfo)
        msg = msginfo['Content']
        if 'group_NickName' in msginfo and re.search(r'直播', msginfo['group_NickName']) and '@query' in msg:
            match = re.search(r'\s*\b(?P<sn>_LC_\w+|\d{8})',msginfo['Content'])
            if match:
                try:
                    sn = match.group('sn')
                    if not sn :
                        return None
                    logger.debug(sn)
                    response = await self.wx.webwxuploadmedia('tmp.png')
                    logger.debug(response)
                    media_id = ""
                    if response is not None:
                        media_id = response['MediaId']
                        self.wx.webwxsendmsgimg(msginfo['FromUserName'], media_id)
                        await asyncio.sleep(1)

                except Exception as e:
                    logger.exception('oop!-------------')
                return None
            #answer = await self.robot.answer(msginfo)
            return answer
