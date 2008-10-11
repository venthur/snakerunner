#! /usr/bin/env python
import wx, sys, os

class SquareMap( wx.Panel ):
	"""Construct a nested-box trees structure view"""
	def __init__( 
		self,  parent=None, id=-1, pos=wx.DefaultPosition, 
		size=wx.DefaultSize, style=wx.TAB_TRAVERSAL|wx.NO_BORDER|wx.FULL_REPAINT_ON_RESIZE, 
		name='SquareMap', model = None,
	):
		super( SquareMap, self ).__init__(
			parent, id, pos, size, style, name
		)
		self.model = model
		self.Bind( wx.EVT_PAINT, self.OnDraw )
#		self.Bind( wx.EVT_SIZE, self.OnResize )
	def setModel( self, model ):
		self.model = model
	def OnDraw( self, event ):
		dc = wx.PaintDC( self )
		if self.model:
			# draw the root box...
			color = wx.Color( 128,128,128 )
			brush = wx.Brush( color  )
			dc.SetBackground( brush )
			dc.Clear()
			w, h = dc.GetSize()
			self.drawBox( dc, self.model, 0,0,w,h )
		else:
			print 'no model'
	SCALE_CHILDREN = .95
	PADDING = 4
	def drawBox( self, dc, node, x,y,w,h, depth=0 ):
		"""Draw a model-node's box and all children nodes"""
		color = wx.Color( (depth * 10)%255, (255-(depth * 10))%255, 255 )
		print ' '*depth, (x,y,w,h)
		brush = wx.Brush( color  )
		dc.SetBrush( brush )
		dc.DrawRectangle( x,y,w,h )
		dc.SetClippingRegion( x,y, w, h )
		dc.DrawText( node.path, x,y,  )
		dc.DestroyClippingRegion()
		x += self.PADDING
		y += self.PADDING*5
		w -= self.PADDING*2
		h -= self.PADDING*6
		if w >0 and h> 0:
			children = self.children( node )
			if children:
				self.layout_children( dc, children, x,y,w,h, depth+1 )
	def layout_children( self, dc, children, x,y,w,h, depth=0 ):
		"""Layout the set of children in the given rectangle"""
		nodes = [ (node.size,node) for node in children ]
		nodes.sort()
		total = sum([size for (size,node) in nodes] )
		if total:
			(firstSize,firstNode) = nodes[-1]
			rest = [node for (size,node) in nodes[:-1]]
			fraction = firstSize/total 
			if w >= h:
				new_w = int(w*fraction)
				if new_w:
					self.drawBox( dc, firstNode, x,y, new_w, h, depth+1 )
				w = w-new_w
				x += new_w 
			else:
				new_h = int(h*fraction)
				if new_h:
					self.drawBox( dc, firstNode, x,y, w, new_h, depth + 1 )
				h = h-new_h
				y += new_h 
			if rest:
				self.layout_children( dc, rest, x,y,w,h, depth )
			else:
				print 'no rest'
	def children( self, node ):
		return node.children
	def value( self, node ):
		return node.size 

class TestApp(wx.App):
	"""Basic application for holding the viewing Frame"""
	def OnInit(self):
		"""Initialise the application"""
		wx.InitAllImageHandlers()
		frame = wx.Frame( None,
		)
		SquareMap( frame, model = self.get_model( sys.argv[1]) )
		frame.Show(True)
		self.SetTopWindow(frame)
		return True
	def get_model( self, path ):
		nodes = []
		for f in os.listdir( path ):
			full = os.path.join( path,f )
			if not os.path.islink( full ):
				if os.path.isfile( full ):
					nodes.append( Node( full, os.stat( full ).st_size, () ) )
				elif os.path.isdir( full ):
					nodes.append( self.get_model( full ))
		return Node( path, sum([x.size for x in nodes]), nodes )

class Node( object ):
	def __init__( self, path, size, children ):
		self.path = path
		self.size = size
		self.children = children 

usage = 'squaremap.py somedirectory'
		
def main():
	"""Mainloop for the application"""
	if not sys.argv[1:]:
		print usage
	else:
		app = TestApp(0)
		app.MainLoop()

if __name__ == "__main__":
	main()
