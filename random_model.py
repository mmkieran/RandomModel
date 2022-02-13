#==============================================================================
#==============================================================================
"""
used to generate random 3D block model deposit data

Kieran M. McDonald
4/7/2017

"""
import wx

from wx.lib import intctrl              #For cells that only take ints
from wx.lib.masked import numctrl       #For cells that only take floats
import wx.lib.scrolledpanel             #Setup scrollbar for the main panel if it is too large

import random

GRAIL = True

try:
    from grail import gsys
    from grail import messages
    from grail.data import pcf
    from grail.data import model
except:
    GRAIL = False
    print "One or more Grail imports failed."

#==============================================================================
# Revision Information
#==============================================================================

REVISION = "$Revision: 3537 $".strip("$Revision: ")
VERSION = "1.0 Build %s" % REVISION


DEPOSIT = ['blob', 'tabular', 'tab(tilted)', 'vein']

class CreateModel(): 
    def __init__(self, row, col, lvl, seed_number, cutoff=0.15, average=1, noise=0.1, min_blocks=0, max_blocks=10, precision=3, deposit = 'blob'):
        
        #Model dimensions
        self.min_row = 0
        self.max_row = row
        self.min_col = 0
        self.max_col = col
        self.min_lvl = 0
        self.max_lvl = lvl
        
        #Model parameters
        self.matrix = []
        self.selected_blocks = []
        self.cutoff = cutoff
        self.seed_number = seed_number
        self.average = average
        self.noise = noise
        self.min_blocks = min_blocks
        self.max_blocks = max_blocks
      
        self.precision = precision
        self.final_grade = 0
        self.deposit_type = deposit

        #Report parameters for the model
        self.total_blocks = 0
        
        self.summary = '----MODEL PARAMETERS----\n\n'
        
        self.summary += 'Deposit type: %s\n' %self.deposit_type
        self.summary += 'Blocks in x: %s\n' %self.max_row
        self.summary += 'Blocks in y: %s\n' %self.max_col
        self.summary += 'Blocks in z: %s\n' %self.max_lvl

        self.summary += 'Number of seeds: %s\n' %self.seed_number
        self.summary += 'Expansion probability: %s\n' %self.cutoff 
        self.summary += 'Average grade: %s\n' %self.average
        self.summary += 'Standard deviation: %s\n' %self.noise
        self.summary += 'Grade precision: %s\n' %self.precision
        self.summary += 'Min blocks: %s\n' %self.min_blocks
        self.summary += 'Max blocks: %s\n' %self.max_blocks
        self.summary += '\n----SEED INFORMATION---\n\n'
        
        #Run main functions (algorithms)
        self.empty_matrix(self.max_row, self.max_col, self.max_lvl)
        self.determine_seeds(self.max_row, self.max_col, self.max_lvl, self.seed_number)

    def empty_matrix(self, row, col, lvl):
        '''Create empty matrix'''
        for x in range(row):
            tmp1 = []
            for y in range(col):
                tmp2 = []
                for z in range(lvl):
                    tmp2.append(-1)
                tmp1.append(tmp2)
            self.matrix.append(tmp1)
        #print "Matrix:\n",  self.print_matrix() #REPORT MATRIX VALUES

    def print_matrix(self):
        '''Print values in matrix'''
        for row in self.matrix:
            print row
        return ''
                    
    def determine_seeds(self, row, col, lvl, seed_number):
        '''Determine location and values for seeds'''
        self.seeds = []
        count = 1
        
        #Create seed locations in model
        for seed in range(seed_number):
            if RandomFrame.select_seed_location.GetValue() == True:
                x = RandomFrame.seed_x.GetValue()-1
                y = RandomFrame.seed_y.GetValue()-1 
                z = RandomFrame.seed_z.GetValue()-1
            else:
                x = random.randint(0,row-1)
                y = random.randint(0,col-1)
                z = random.randint(0,lvl-1)

            self.pref_d, self.opp_d = self.anisotropy()
            
            #Append new seed to list
            current_seed = [x,y,z]
            self.seeds.append([x,y,z])
            
            #Generate random gaussian value for seed
            self.seed_value = round(random.gauss(self.average,self.noise),self.precision)
            
            #Add seed and value to matrix
            self.matrix[x][y][z] = self.seed_value
            self.block_count = 1
            
            #Find neighbors for seed
            self.check_blocks([[current_seed]])
            
            #Write to report
            self.summary += "Seed %s value: %s\n" %(count,self.seed_value)
            self.summary += "Block count: %s\n" %self.block_count
            self.summary += "Seed coordinate: %s, %s, %s\n\n" %(x+1,y+1,z+1)
            
            self.total_blocks += self.block_count
            count += 1
            
        self.summary +=  "Total blocks coded: %s\n" %self.total_blocks
        #print "\nNEW Matrix:\n",  self.print_matrix()   #REPORT MATRIX VALUES

    def find_neighbors(self, row, col, lvl):
        '''Find blocks neighboring the current block (based on row, col, lvl) and see if they meet the criteria for coding.
        Selected blocks are then checked for neighbors that meet the coding criteria recursively.'''
        
        steps = [0,1,-1]
        neighborhood = []
        
        for i in steps:
            for j in steps:
                for k in steps:
                    #Check if we have exceeded the max number of blocks to code
                    if self.block_count >= self.max_blocks:
                        return neighborhood
                    
                    if self.check_model_range(row+i, col+j, lvl+k) == False:
                        continue
                    
                    if self.matrix[row+i][col+j][lvl+k] != -1:
                        continue

                    preference = 0
                    if [i,j,k] in self.pref_d or [i,j,k] in self.opp_d:
                        preference = .9 #Parameterize this
                        
                    if random.random() <= (self.cutoff + preference) or self.block_count < self.min_blocks:
                        gauss = random.gauss(self.seed_value, self.noise)
                        self.matrix[row+i][col+j][lvl+k] = round(gauss,self.precision)
                        self.block_count += 1
                        neighborhood.append([row+i, col+j, lvl+k])
                        
                        if self.deposit_type == 'vein':
                            if random.random() > 0.9:
                                self.pref_d, self.opp_d = self.anisotropy()
                                
                    else:
                        self.matrix[row+i][col+j][lvl+k] = -2
        return neighborhood

    def check_blocks(self, neighborhoods):

        #Check if there are no neighboring blocks around target block
        if len(neighborhoods) < 1:
            return
        
        to_check = []
        for blocks in neighborhoods:
            if len(blocks) < 1:
                continue
            for block in blocks:
                x = block[0]
                y = block[1]
                z = block[2]
                neighborhood = self.find_neighbors(x, y, z)
                
                if len(neighborhood) >= 1:
                    to_check.append(neighborhood)
                    
        if len(to_check) >= 1:
            self.check_blocks(to_check)
        else:
            return

    
    def check_model_range(self, row, col, lvl):

        #Check model boundaries to see if the proposed block exists
        if row > self.max_row -1 or row < self.min_row:
            return False
        if col > self.max_col -1 or col < self.min_col:
            return False
        if lvl > self.max_lvl -1 or lvl < self.min_lvl:
            return False

    def anisotropy(self):
        #Remeber that column increments EAST and row increments NORTH in MS3D query
        pref_d = []
        opp = []
        
        #Check the type of deposit and determine the preferential directions for seed expansion
        if self.deposit_type == 'vein':
            pref_d = [ [random.randint(-1,1) for x in range(0,3)] ] #Vein in random direction
            opp = [ [-x for x in pref_d[0]] ]     

        elif self.deposit_type == 'blob':
            pref_d = [] #No preferential direction            
            
        elif self.deposit_type == 'tabular':
            pref_d = []
            pref_d = [ [1,0,0], [1,1,0], [1,-1,0], [-1,0,0], [-1,1,0], [-1,-1,0], [0,1,0], [0,-1,0] ] #Tabular deposit with no dip
        
        elif self.deposit_type == 'tab(tilted)':
            #Generate a tabular deposit with a random dip
            dip_dict = {'N': [1,0,1], 'NE': [1,1,1], 'NW': [1,-1,1], 'S': [-1,0,1], 'SE': [-1,1,1], 'SW': [-1,-1,1], 'E': [0,1,1], 'W': [0,-1,1]}

            dip = random.choice( dip_dict.keys() )
            coord = dip_dict[dip]
            
            #Determine dip directions that are close to the one we chose (e.g. N is close to NE)
            if len(dip) > 1:
                pref_d.append( dip_dict[dip] )
                pref_d.append( dip_dict[dip[0]] )
                pref_d.append( dip_dict[dip[1]] )
                tmp = coord[:]
                tmp[0] = -tmp[0]
                pref_d.append( tmp[0:2] + [0] )
            
            elif len(dip) == 1:
                pref_d.append(coord)

                if coord[0] == 0:
                    tmp = coord[:]
                    tmp[0] = 1
                    pref_d.append(tmp)
                    
                    tmp2 = coord[:]
                    tmp2[0] = -1
                    pref_d.append(tmp2)
                    
                    tmp3 = tmp[:]
                    tmp3[1] = 0
                    pref_d.append(tmp3[0:2] + [0])
                    
                elif coord[1] == 0:
                    tmp = coord[:]
                    tmp[1] = 1
                    pref_d.append(tmp)
                    
                    tmp2 = coord[:]
                    tmp2[1] = -1
                    pref_d.append(tmp2)
                    
                    tmp3 = tmp[:]
                    tmp3[0] = 0
                    pref_d.append(tmp3[0:2] + [0])

            #Get the opposite dip directions for everything (e.g. Opposite of NE is SW)
            opp = []
            for item in pref_d:
                tmp = [-x for x in item ]
                opp.append(tmp)

            #These become our preferential directions for the tab deposit
            pref_d = pref_d + opp
            
        else:  
            pass
        
        return pref_d, opp
                
    
    def write_matrix_csv(self):
        '''Use this method to write a file representing the 2D matrix.'''
        fileName = 'model.txt'
        csv = open(fileName, 'w')
        report = open('model_params.txt','w')        
        for row_idx, row in enumerate(self.matrix):
            for col_idx, col in enumerate(row):
                for lvl_idx, value in enumerate(col): 
                    csv.write(str(col_idx+1) + ',')
                    csv.write(str(row_idx+1) + ',')
                    csv.write(str(lvl_idx+1) + ',')
                    csv.write('%0.3f' %value)
                    if lvl_idx != len(col)-1:
                        csv.write('\n')
                if col_idx != len(row)-1:
                    csv.write('\n')
            csv.write('\n')
        report.write(self.summary)
        print self.summary
        report.close()
        csv.close()

    def code_model(self, pcf, file15, item, reset):
        '''Code the matrix values to the model if using a PCF'''
        summary = ""
        
        if not pcf or not file15 or not item:
            print "PCF, model, or items not defined..."
            return
        
        for lvl in xrange(self.min_lvl+1, self.max_lvl+1):
            m = model.Model(pcf, file15, lvl, lvl, self.min_row+1, self.max_row, self.min_col+1, self.max_col, [item])
            s = m.slab()
            for col in xrange(self.min_col+1, self.max_col+1):
                for row in xrange(self.min_row+1, self.max_row+1):
                    val = self.matrix[row-1][col-1][lvl-1]
                    if val != -1 and val != -2:
                        s.modset(item, lvl, row, col, val)  #store the value of the item at this location
                    elif reset == True:
                        val = model.UNDEFINED
                        s.modset(item, lvl, row, col, val)  #store the value of the item at this location
            m.storeslab() # save our calculation results to file
            m.free()      # explicitly free up memory

        #Write the PCF information to model_params.txt
        summary += "----PCF INFO----\n\n"
        summary += "PCF path: %s\n" %(pcf)
        summary += "Model name: %s\n" %file15
        summary += "Model item: %s\n" %item
        summary += "Reset model item: %s\n\n" %reset

        self.summary = summary + self.summary

class myFrame(wx.Frame):
    '''This builds the main panel of the GUI.'''
    
    def __init__(self, parent, title):
        '''Frame = Window. Run the main methods of the class'''
        wx.Frame.__init__(self, parent, title=title, size=(700,900))
        #self.panel = wx.Panel(self, -1)
        
        self.panel = wx.lib.scrolledpanel.ScrolledPanel(self,-1, style=wx.SIMPLE_BORDER) #Replace regular panel with scrollbar panel
        self.panel.SetupScrolling()

        #Create a dictionary to house the initial values
        self.params = {'Blocks in x': 10.0, 'Blocks in y': 10.0, 'Blocks in z': 10.0, 'Number of seeds': 1, 'Expansion probability': .15, 'Average grade': 1.0, 'Standard deviation': 0.1, 'Min blocks': 0.0, 'Max blocks': 10, 'Grade precision': 2, 'Deposit type': 'blob'}
        
        #Attempt to read the values from the model_params.txt file if it exists (last used values)
        self.open_ini_file()

        #Generate outlines around each section of the window
        self.static1 = wx.StaticBox(self.panel, label= 'Description')
        self.staticSizer1 = wx.StaticBoxSizer(self.static1, wx.VERTICAL)
        
        self.static2 = wx.StaticBox(self.panel, label= 'MineSight Model Integration')
        self.staticSizer2 = wx.StaticBoxSizer(self.static2, wx.VERTICAL)

        self.static3 = wx.StaticBox(self.panel, label= 'Deposit Generation Parameters')
        self.staticSizer3 = wx.StaticBoxSizer(self.static3, wx.VERTICAL)

        #Tool description widgets (header)
        self.header_text = '''\nRandomly generates values for a single item in a model of a given size.    \n
The row, column, bench, and item values will be output to a CSV file.\n 
You can also load directly to a 3DBM in MineSight using a PCF file.
'''
        self.header = wx.StaticText(self.panel,id=wx.ID_ANY,label=self.header_text)
        
        self.staticSizer1.Add(self.header)
        
        #PCF widget setup
        self.FILE10 = None
        self.FILE15 = None
        self.ITEM = None

        self.pcf_path = wx.StaticText(self.panel,label='', style= wx.ALIGN_BOTTOM)
        self.no_grail = wx.StaticText(self.panel,label='', style= wx.ALIGN_BOTTOM)
        self.model_desc = wx.StaticText(self.panel,label='Model: ')
        self.item_desc = wx.StaticText(self.panel,label='Model item: ')

        self.use_pcf_checkbox = wx.CheckBox(self.panel, label='Load directly into PCF?')
        self.select_pcf_button = wx.Button(self.panel, label='Select PCF')
        self.models = wx.ComboBox(self.panel, choices=[], style= wx.CB_READONLY | wx.CB_SORT)
        self.items = wx.ComboBox(self.panel, choices=[], style= wx.CB_READONLY | wx.CB_SORT)
        self.reset_item_checkbox = wx.CheckBox(self.panel, label='Reset model item?')

        #Disable the use PCF checkbox if the grail import failed
        if not GRAIL:
            self.use_pcf_checkbox.Disable()
            self.no_grail.SetLabel('Grail import failed')
            self.no_grail.SetForegroundColour('blue')
        self.select_pcf_button.Disable()
        self.models.Disable()
        self.items.Disable()
        self.reset_item_checkbox.Disable()
        
        #Establish how pcf widget events will be handled
        self.Bind(wx.EVT_BUTTON, self.get_pcf_and_models, self.select_pcf_button)
        self.Bind(wx.EVT_CHECKBOX, self.use_pcf, self.use_pcf_checkbox)
        self.Bind(wx.EVT_COMBOBOX, self.get_model_items, self.models)
        self.Bind(wx.EVT_COMBOBOX, self.get_code_item, self.items)

        #Put all the pcf widgets in a Sizer
        self.gbsizer = wx.GridBagSizer(hgap=1, vgap=1)
        self.gbsizer.Add(self.use_pcf_checkbox, pos=(0,0),span=(1,2), flag=wx.TOP | wx.LEFT | wx.BOTTOM, border=5)
        self.gbsizer.Add(self.no_grail, pos=(0,2),span=(1,3), flag=wx.TOP | wx.LEFT | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT, border=5)
        self.gbsizer.Add(self.select_pcf_button, pos=(1,0),span=(1,1), flag=wx.TOP | wx.LEFT, border=5)
        self.gbsizer.Add(self.pcf_path, pos=(1,1),span=(1,3), flag=wx.TOP | wx.LEFT | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT, border=5)
        self.gbsizer.Add(self.model_desc, pos=(2,0),span=(1,1), flag=wx.TOP | wx.LEFT, border=5)
        self.gbsizer.Add(self.models, pos=(2,1),span=(1,1), flag=wx.TOP | wx.LEFT, border=5)
        self.gbsizer.Add(self.item_desc, pos=(3,0),span=(1,1), flag=wx.TOP | wx.LEFT, border=5)
        self.gbsizer.Add(self.items, pos=(3,1),span=(1,1), flag=wx.TOP | wx.LEFT, border=5)
        self.gbsizer.Add(self.reset_item_checkbox, pos=(4,1),span=(1,1), flag=wx.TOP | wx.LEFT | wx.BOTTOM, border=5)
        
        self.staticSizer2.Add(self.gbsizer)

        #Model generation widgets
        self.deposit = wx.ComboBox(self.panel, choices=DEPOSIT, style= wx.CB_READONLY, value= self.params['Deposit type'])
        self.nx = intctrl.IntCtrl(self.panel,value=int(self.params['Blocks in x']))
        self.ny = intctrl.IntCtrl(self.panel,value=int(self.params['Blocks in y']))
        self.nz = intctrl.IntCtrl(self.panel,value=int(self.params['Blocks in z']))
        
        self.nx.Bind(wx.EVT_KILL_FOCUS, lambda evt: self.seed_x.SetMax(self.nx.GetValue()))
        self.ny.Bind(wx.EVT_KILL_FOCUS, lambda evt: self.seed_y.SetMax(self.ny.GetValue()))
        self.nz.Bind(wx.EVT_KILL_FOCUS, lambda evt: self.seed_z.SetMax(self.nz.GetValue()))
        
        #Seed location
        self.select_seed_location = wx.CheckBox(self.panel, label='Select seed location?')
        self.seed_x_desc = wx.StaticText(self.panel,label='Row ')
        self.seed_x = intctrl.IntCtrl(self.panel, value=1, min=1, max=self.nx.GetValue(), limited=True)
        
        self.seed_y_desc = wx.StaticText(self.panel,label='Column ')
        self.seed_y = intctrl.IntCtrl(self.panel, value=1, min=1, max=self.ny.GetValue(), limited=True)
        
        self.seed_z_desc = wx.StaticText(self.panel,label='Bench ')
        self.seed_z = intctrl.IntCtrl(self.panel, value=1, min=1, max=self.nz.GetValue(), limited=True)
        
        self.Bind(wx.EVT_CHECKBOX, self.seed_location, self.select_seed_location)
        self.seed_x.Disable()
        self.seed_y.Disable()
        self.seed_z.Disable()
        
        self.starting_seeds = intctrl.IntCtrl(self.panel,value=int(self.params['Number of seeds']))
        self.chance_to_code = numctrl.NumCtrl(self.panel,integerWidth= 10, fractionWidth= 3, min= 0, max=1, value=self.params['Expansion probability'])
        self.average = numctrl.NumCtrl(self.panel,integerWidth= 10, fractionWidth= 2, min= 0, value=self.params['Average grade'])
        self.stdev = numctrl.NumCtrl(self.panel,integerWidth= 10, fractionWidth= 2, min= 0, value=self.params['Standard deviation'])
        self.decimals = intctrl.IntCtrl(self.panel,value=int(self.params['Grade precision']))
        self.min_blocks = intctrl.IntCtrl(self.panel,value=int(self.params['Min blocks']))
        self.max_blocks = intctrl.IntCtrl(self.panel,value=int(self.params['Max blocks']))

        #Descriptions of each generation option
        self.nx_desc = wx.StaticText(self.panel,label='Number of blocks in x ')
        self.ny_desc = wx.StaticText(self.panel,label='Number of blocks in y ')
        self.nz_desc = wx.StaticText(self.panel,label='Number of blocks in z ')
  
        self.deposit_desc = wx.StaticText(self.panel,label='Deposit type ')  
        self.seed_desc = wx.StaticText(self.panel,label='Seeds to grow in model ')
        self.chance_desc = wx.StaticText(self.panel,label='Expansion chance (non-preferential) ')
        self.avg_desc = wx.StaticText(self.panel,label='Average value of model item ')
        self.stdev_desc = wx.StaticText(self.panel,label='Standard deviation of model item ')
        self.decimal_desc = wx.StaticText(self.panel,label='Precision of model item ')
        self.min_desc = wx.StaticText(self.panel,label='Min blocks before seed can stop ')
        self.max_desc = wx.StaticText(self.panel,label='Max blocks seed can code ')

        #Place all model generation widgets in a sizer
        self.vbox = wx.GridBagSizer(hgap=1, vgap=3) 
        self.gridSizer = wx.GridBagSizer(hgap=5, vgap=5)

        self.gridSizer.Add(self.deposit_desc, pos=(0,0), span=(1,1), flag=wx.EXPAND | wx.ALL)                   
        self.gridSizer.Add(self.deposit, pos=(0,1), span=(1,1), flag=wx.ALL)  
        
        self.gridSizer.Add(self.nx_desc, pos=(1,0), span=(1,1), flag=wx.EXPAND | wx.ALL)
        self.gridSizer.Add(self.nx, pos=(1,1), span=(1,1), flag=wx.ALL)

        self.gridSizer.Add(self.ny_desc, pos=(2,0), span=(1,1), flag=wx.EXPAND | wx.ALL)
        self.gridSizer.Add(self.ny, pos=(2,1), span=(1,1), flag=wx.ALL)

        self.gridSizer.Add(self.nz_desc, pos=(3,0), span=(1,1), flag=wx.EXPAND | wx.ALL)
        self.gridSizer.Add(self.nz, pos=(3,1), span=(1,1), flag=wx.ALL)

        self.gridSizer.Add(self.seed_desc, pos=(4,0), span=(1,1), flag=wx.EXPAND | wx.ALL)
        self.gridSizer.Add(self.starting_seeds, pos=(4,1), span=(1,1), flag=wx.ALL)
        
        self.gridSizer.Add(self.chance_desc, pos=(5,0), span=(1,1), flag=wx.ALL)
        self.gridSizer.Add(self.chance_to_code, pos=(5,1), span=(1,1), flag=wx.ALL)

        self.gridSizer.Add(self.avg_desc, pos=(6,0), span=(1,1), flag=wx.EXPAND | wx.ALL)
        self.gridSizer.Add(self.average, pos=(6,1), span=(1,1), flag=wx.ALL)

        self.gridSizer.Add(self.stdev_desc, pos=(7,0), span=(1,1), flag=wx.EXPAND | wx.ALL)        
        self.gridSizer.Add(self.stdev, pos=(7,1), span=(1,1), flag=wx.ALL)

        self.gridSizer.Add(self.decimal_desc, pos=(8,0), span=(1,1), flag=wx.EXPAND | wx.ALL)
        self.gridSizer.Add(self.decimals, pos=(8,1), span=(1,1), flag=wx.ALL)     

        self.gridSizer.Add(self.min_desc, pos=(9,0), span=(1,1), flag=wx.EXPAND | wx.ALL)                                    
        self.gridSizer.Add(self.min_blocks, pos=(9,1), span=(1,1), flag=wx.ALL)

        self.gridSizer.Add(self.max_desc, pos=(10,0), span=(1,1), flag=wx.EXPAND | wx.ALL)                                    
        self.gridSizer.Add(self.max_blocks, pos=(10,1), span=(1,1), flag=wx.ALL)   

        #Select starting location for seed
        self.gridSizer.Add(self.select_seed_location, pos=(0,2), span=(1,1), flag=wx.ALL)
        self.gridSizer.Add(self.seed_x_desc, pos=(1,2), span=(1,1), flag=wx.EXPAND | wx.ALL)
        self.gridSizer.Add(self.seed_x, pos=(1,3), span=(1,1), flag=wx.ALL)

        self.gridSizer.Add(self.seed_y_desc, pos=(2,2), span=(1,1), flag=wx.EXPAND | wx.ALL)
        self.gridSizer.Add(self.seed_y, pos=(2,3), span=(1,1), flag=wx.ALL)

        self.gridSizer.Add(self.seed_z_desc, pos=(3,2), span=(1,1), flag=wx.EXPAND | wx.ALL)
        self.gridSizer.Add(self.seed_z, pos=(3,3), span=(1,1), flag=wx.ALL)        

        self.staticSizer3.Add(self.gridSizer)

        #Run and Close buttons
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.okButton = wx.Button(self.panel, label = 'Run it')
        self.quitButton = wx.Button(self.panel, label = 'Quit')
        
        #Event binding for run and close buttons
        self.Bind(wx.EVT_BUTTON, self.onOK, self.okButton)
        self.Bind(wx.EVT_BUTTON, self.onQuit, self.quitButton)

        #Put run and close buttons in sizer
        self.hbox.Add(self.quitButton)
        self.hbox.Add((280,-1))  
        self.hbox.Add(self.okButton)
        
        self.vbox.Add(self.hbox, pos=(3,0),span=(1,1), flag=wx.TOP | wx.LEFT, border=30)
        
        #Stack the three tool sections vertically in a sizer
        self.vbox.Add(self.staticSizer1, pos=(0,0),span=(1,1),flag=wx.TOP | wx.LEFT, border=30)
        self.vbox.Add(self.staticSizer2, pos=(1,0),span=(1,1),flag=wx.TOP | wx.LEFT | wx. EXPAND, border=30)
        self.vbox.Add(self.staticSizer3, pos=(2,0),span=(1,1),flag=wx.TOP | wx.LEFT, border=30)
        self.panel.SetSizer(self.vbox)
        
        self.Show()

    def open_ini_file(self):
        try:
            report = open('model_params.txt','r')
            for idx, line in enumerate(report.readlines()):
                
                if ":" in line:
                    split = line.split(":")
                    if len(split) > 1:
                        strip = split[1].strip()
                        try:
                            self.params[split[0]] = eval(strip)
                        except:
                            self.params[split[0]] = strip
                        
                if "SEED" in line:
                    break
            
        except:
            print "No model_params.txt file found. Using default settings."
            
    def seed_location(self, e):
        if self.select_seed_location.GetValue() == True:
            self.seed_x.Enable()
            self.seed_y.Enable()
            self.seed_z.Enable()
            self.starting_seeds.Disable()
            self.starting_seeds.SetValue(1)

        else:
            self.seed_x.Disable()
            self.seed_y.Disable()
            self.seed_z.Disable()
            self.starting_seeds.Enable()

    def use_pcf(self, e):
        if self.use_pcf_checkbox.GetValue() == True:
            self.select_pcf_button.Enable()
            self.models.Enable()
            self.items.Enable()
            self.reset_item_checkbox.Enable()
            self.nx.Disable()
            self.ny.Disable()
            self.nz.Disable()
        else:
            self.select_pcf_button.Disable()
            self.models.Disable()
            self.items.Disable()
            self.reset_item_checkbox.Disable()
            self.nx.Enable()
            self.ny.Enable()
            self.nz.Enable()        

    def get_pcf_and_models(self, e):
        self.models.Clear()
        self.items.Clear()
        file_browser = wx.FileDialog(self.panel, message= 'Select PCF', wildcard='*10.dat',style=wx.FD_OPEN)
        file_browser.ShowModal()
        pcf_loc = file_browser.GetPath()
        self.FILE10 = pcf.Pcf(pcf_loc)
        self.pcf_path.SetLabel(pcf_loc)
        self.pcf_path.SetForegroundColour('blue')

        try:
            self.nx.SetValue(self.FILE10.nx())
            self.ny.SetValue(self.FILE10.ny())
            self.nz.SetValue(self.FILE10.nz())
        except:
            print "Couldn't set x,y,z values"
        
        try:
            self.seed_x.SetMax(self.nx.GetValue())
            self.seed_y.SetMax(self.ny.GetValue())
            self.seed_z.SetMax(self.nz.GetValue())
        except:
            print "Couldn't set seed location max..."
        
        models = self.FILE10.filelistbytype(15)
        self.models.SetItems(models)

    def get_model_items(self, e):
        self.items.Clear()
        self.FILE15 = self.models.GetValue()
        items = self.FILE10.itemlist(self.FILE15)
        self.items.SetItems(items)

    def get_code_item(self, e):
        self.ITEM = self.items.GetValue()

    
    def onOK(self,e):
        print "Starting up...\n"
        x = self.nx.GetValue()
        y = self.ny.GetValue()
        z = self.nz.GetValue()
        
        seeds = self.starting_seeds.GetValue() 
        prob = self.chance_to_code.GetValue()
        avg = self.average.GetValue() 
        stdev = self.stdev.GetValue() 
        minb = self.min_blocks.GetValue()
        maxb = self.max_blocks.GetValue()
        prec = self.decimals.GetValue() 
        deposit = self.deposit.GetValue()
            
        matrix = CreateModel(x,y,z,seeds,prob,avg,stdev,minb,maxb,prec,deposit)
        
        if self.use_pcf_checkbox.GetValue() == True:
            matrix.code_model(self.FILE10.path(), self.FILE15, self.ITEM, self.reset_item_checkbox.GetValue())
        
        matrix.write_matrix_csv()
        
        print "Done"
        dial = wx.MessageBox(matrix.summary + '\n\nCLOSE?','Info', wx.YES_NO | wx.ICON_INFORMATION)
        if dial == wx.YES:
            self.Destroy()
            
        del matrix
        
    def onQuit(self, e):
        self.Destroy()    

def main():
    app = wx.App()
    title = "Random Model Generator v%s" % VERSION
    global RandomFrame
    RandomFrame = myFrame(None, title)
    app.MainLoop()

def gmain(message,data):
    if message == messages.gRUN:
        main()
    else:
        return gsys.grailmain(message, data)

if __name__ == '__main__':
    print "Running stand-alone mode..."
    main()
