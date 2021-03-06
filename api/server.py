#!/usr/bin/python

import cherrypy
from cherrypy._cperror import HTTPError
from cherrypy.lib import sessions
import wrapper
import json
import random
import os
import argparse

from py2neo.neo4j import Direction

JSON_OK = { "message": "ok"}

parser = argparse.ArgumentParser();
parser.add_argument("--port", default = 8082, type = int)
args = parser.parse_args();

class Api(object):
	wrapper = wrapper.Wrapper()

	@cherrypy.expose
	def tag(self, *path, **args):
		if self.wrapper.hasItemGotTag(int(args['item']), int(args['tag'])):
			self.wrapper.untag(int(args['item']), int(args['tag']));
		else:
			self.wrapper.tag(int(args['item']), int(args['tag']));

		return self.outputJson(JSON_OK);

	@cherrypy.expose
	def listUpdate(self, *path, **args):
		self.wrapper.updateList(int(args['list']), args['title'], args['sort'])

		return self.outputJson(JSON_OK);

	@cherrypy.expose
	def setDueDate(self, *path, **args):
		self.wrapper.setDueDate(int(args['item']), args['dueDate'])

		return self.outputJson(JSON_OK);

	@cherrypy.expose
	def default(self, *args, **kwargs):
		return "wt API"

	def outputJson(self, structure):
		cherrypy.response.headers['Content-Type'] = 'application/json'

		return json.dumps(structure);

	@cherrypy.expose
	def createTag(self, *path, **args):
		self.wrapper.createTag(self.getUsername(), args['title'])

		return self.outputJson(JSON_OK);

	@cherrypy.expose
	def listTags(self, *path, **args):
		tags = self.wrapper.getTags(self.getUsername());

		ret = []

		for row in tags:
			singleTag = row[0]

			ret.append({
				"id": singleTag.id,
				"title": singleTag['title'],
				"shortTitle": singleTag['shortTitle']
			});

		return self.outputJson(ret);

	@cherrypy.expose
	def listLists(self, *path, **args):
		lists = self.wrapper.getLists(self.getUsername());

		ret = []

		for row in lists:
			singleList = row[0]

			ret.append({
				"id": singleList.id,
				"title": singleList['title'],
				"sort": singleList['sort'],
				"count": len(singleList.get_related_nodes(Direction.OUTGOING))
			})

		return self.outputJson(ret)

	@cherrypy.expose
	def createList(self, *path, **args):
		self.wrapper.createList(self.getUsername(), args["title"]);

		return self.outputJson(JSON_OK);

	@cherrypy.expose
	def createTask(self, *path, **args):
		if (args['parentType'] == "list"):
			createdItems = self.wrapper.createListItem(int(args['parentId']), args['content'])
		else:
			createdItems = self.wrapper.createSubItem(int(args['parentId']), args['content'])

		for row in createdItems:
			item = row[0]

			return self.outputJson(self.normalizeItem(item));


	def getItemTags(self, singleItem):
		ret = []

		for tag in singleItem.get_related_nodes(Direction.EITHER, "tagged"):
			ret.append({
				"id": tag.id,
				"title": tag['title']
			});

		return ret;

	def normalizeItem(self, singleItem):
		return {
			"hasChildren": (len(singleItem.get_related_nodes(Direction.OUTGOING, 'owns')) > 0),
			"content": singleItem['content'],
			"tags": self.getItemTags(singleItem),
			"dueDate": singleItem['dueDate'],
			"id": singleItem.id
		}

	@cherrypy.expose
	def listTasks(self, *path, **args):
		if "task" in args:
			items = self.wrapper.getSubItems(int(args['task']))
		else:
			items = self.wrapper.getItemsFromList(int(args['list']), args['sort'])

		ret = []
		for row in items: 
			singleItem = row[0]

			ret.append(self.normalizeItem(singleItem))

		return self.outputJson(ret);

	@cherrypy.expose
	def deleteTask(self, *path, **args):
		self.wrapper.deleteTask(int(args['id']))

		return self.outputJson(JSON_OK);

	@cherrypy.expose
	def deleteList(self, *path, **args):
		self.wrapper.deleteList(int(args['id']));

		return self.outputJson(JSON_OK);

	def outputJsonError(self, code, msg):
		cherrypy.response.status = code;

		return self.outputJson({
			"type": "Error",
			"message": msg
		})

	@cherrypy.expose
	def register(self, *path, **args):
		try:
			if len(args['username']) < 3:
				raise Exception("Username must be at least 3 characters long.")

			if len(args['password']) < 6:
				raise Exception("Password must be at least 6 character long.");

			api.wrapper.register(args['username'], args['password'], args['email'])
		except Exception as e:
			return self.outputJsonError(403, str(e))

	def randomWallpaper(self):
		wallpapers = []

		try:
			wallpapers = []
			
			for wallpaper in os.listdir("../wallpapers"):
				if wallpaper.endswith(".png") or wallpaper.endswith(".jpg"):
					wallpapers.append(wallpaper)
		except Exception as e:
			print e

		if len(wallpapers) == 0:
			return None
		else:
			return random.choice(wallpapers);

	@cherrypy.expose
	def init(self, *path, **args):
		username = None

		if "username" not in cherrypy.session:
			cherrypy.session['username'] = None
			cherrypy.session.save();
		else:
			username = cherrypy.session['username']

		return self.outputJson({
			"wallpaper": self.randomWallpaper(),
			"id": cherrypy.session.id,
			"username": username
		});

	def isLoggedIn(self):
		if "username" in cherrypy.session:
			if cherrypy.session['username'] != None:
				return True

		return False

	def checkLoggedIn(self):
		if not self.isLoggedIn():
			raise cherrypy.HTTPError(403, "Login required.")
	
	def getUsername(self):
		self.checkLoggedIn();

		return cherrypy.session['username']

	@cherrypy.expose
	def updateTag(self, *path, **args):
		updatedTag = self.wrapper.updateTag(int(args['id']), args['newTitle'], args['shortTitle'])

		return self.outputJson(updatedTag)

	@cherrypy.expose
	def authenticate(self, *path, **args):
		user, password = api.wrapper.getUser(args['username']);

		if user == None:
			return self.outputJsonError(403, "User not found: " + args['username'])

		if args['password'] != password:
			return self.outputJsonError(403, "Password is incorrect.")

		cherrypy.session.regenerate();
		cherrypy.session['username'] = user['username'];
		cherrypy.session.save();

		return self.outputJson(user);

	@cherrypy.expose
	def logout(self, *path, **args):
		cherrypy.session['username'] = None
		cherrypy.session.regenerate();

		return self.outputJson({"message": "Logged out!"})
		
def CORS():
	cherrypy.response.headers['Access-Control-Allow-Origin'] = "http://wacky-tracky.teratan.net"
	cherrypy.response.headers['Access-Control-Allow-Credentials'] = "true"

api = Api();

cherrypy.config.update({
	'server.socket_host': '0.0.0.0',
	'server.socket_port': args.port,
	'tools.sessions.on': True,
	'tools.sessions.storage_type': 'ram',
#	'tools.sessions.storage_path': './sessions',
	'tools.sessions.timeout': 60,
	'tools.CORS.on': True,
});

cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS);

cherrypy.quickstart(api)
