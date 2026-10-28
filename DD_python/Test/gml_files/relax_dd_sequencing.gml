graph [
	 directed 1
	 hierarchic 1

 node [
	 id 0
	 label "[]_-1"
 	graphics [
	 type "ellipse"
	 hasFill 0
	 w 90.0   h 110.0
	 outline "#000000" ]
 	LabelGraphics [
	 text "Nodo 0"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "t"
]
 	LabelGraphics [
	 text "[]_-1"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "c"
]
]

 node [
	 id 1
	 label "[0]_0"
 	graphics [
	 type "ellipse"
	 hasFill 0
	 w 90.0   h 110.0
	 outline "#000000" ]
 	LabelGraphics [
	 text "Nodo 1"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "t"
]
 	LabelGraphics [
	 text "[0]_0"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "c"
]
]

 node [
	 id 2
	 label "[1]_1"
 	graphics [
	 type "ellipse"
	 hasFill 0
	 w 90.0   h 110.0
	 outline "#000000" ]
 	LabelGraphics [
	 text "Nodo 2"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "t"
]
 	LabelGraphics [
	 text "[1]_1"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "c"
]
]

 node [
	 id 3
	 label "[2]_2"
 	graphics [
	 type "ellipse"
	 hasFill 0
	 w 90.0   h 110.0
	 outline "#000000" ]
 	LabelGraphics [
	 text "Nodo 3"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "t"
]
 	LabelGraphics [
	 text "[2]_2"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "c"
]
]

 node [
	 id 4
	 label "[2]_2"
 	graphics [
	 type "ellipse"
	 hasFill 0
	 w 90.0   h 110.0
	 outline "#000000" ]
 	LabelGraphics [
	 text "Nodo 4"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "t"
]
 	LabelGraphics [
	 text "[2]_2"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "c"
]
]

 node [
	 id 5
	 label "[1]_2"
 	graphics [
	 type "ellipse"
	 hasFill 0
	 w 90.0   h 110.0
	 outline "#000000" ]
 	LabelGraphics [
	 text "Nodo 5"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "t"
]
 	LabelGraphics [
	 text "[1]_2"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "c"
]
]

 node [
	 id 6
	 label "[0, 2]_0"
 	graphics [
	 type "ellipse"
	 hasFill 0
	 w 90.0   h 110.0
	 outline "#000000" ]
 	LabelGraphics [
	 text "Nodo 6"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "t"
]
 	LabelGraphics [
	 text "[0, 2]_0"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "c"
]
]

 node [
	 id 7
	 label "[]_-1"
 	graphics [
	 type "ellipse"
	 hasFill 0
	 w 90.0   h 110.0
	 outline "#000000" ]
 	LabelGraphics [
	 text "Nodo 7"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "t"
]
 	LabelGraphics [
	 text "[]_-1"
	 fontSize 12
	 fontName "Dialog"
	 model "internal"
	 anchor "c"
]
]

edge [
	 source 0
	target 1
	label "0"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 0
	target 2
	label "1"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 0
	target 3
	label "2"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 1
	target 5
	label "1"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 1
	target 4
	label "2"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 2
	target 5
	label "0"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 2
	target 5
	label "2"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 3
	target 6
	label "0"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 3
	target 4
	label "1"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 4
	target 7
	label "0"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 4
	target 7
	label "1"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 5
	target 7
	label "0"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 5
	target 7
	label "2"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]

edge [
	 source 6
	target 7
	label "1"
	graphics [
	fill "#000000" 		targetArrow "standard"	 	 
]]
]