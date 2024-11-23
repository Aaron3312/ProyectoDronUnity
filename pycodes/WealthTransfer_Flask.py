
#Import agentpy for ABM
import agentpy as ap

# Import visualization libraries
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# Import os utilities
import os
import signal

# Importing flask module for a WSGI application
# Additionally, importing json and request utilities
from flask import Flask, jsonify, request

#########################################################
#                   Flask Server                        #
#########################################################

# Flask constructor takes the name of 
# current module (__name__) as argument.
app = Flask(__name__)

# Create new POST EndPoint to /step
@app.route('/step', methods=['POST'])
def step():
    """ 
    A step function from the POST endpoint.
    It will run all necessary functions to execute 
    the next simulation iteration.

    It verifies if the simulation is still running. It it is not,
    then it will kill the server (and send a trigger to the client).
    """
    # if model.running:
    """
    If the simulation is still running, call functions to 
    execute the next iteration.

    First, updates the model environment (AgentList) by getting 
    the wealth of all agents (from the client). Then, calls the 
    model step (manually, not by model.run()), and its update 
    method. Finally, it sends a JSON response with all next 
    actions of the agents.
    """
    # Converts the list of wealths into an AttrIter (list of atributes)
    # and updates the wealth of all agents
    model.agents.wealth = ap.AttrIter(eval(request.form['wealthList']))
    # Executes model's step() manually (this is 'model.sim_step()', 
    # instead of model.step()) (See more in the agentpy's documentation)
    model.sim_step()
    # Calls model's update()
    model.update()
    # Send a JSON response with the list of next actions 
    # (see the class WealthModel)
    return jsonify({'actions' : model.actions})
    # else:
    """
    If the simulation is not running, then kill the server.
    it calls the kill function from OS (it can have different
    name on diferent OSs) by identifying this server's PID.
    """
        # # Kill this server PID
        # os.kill(os.getpid(), signal.SIGINT)
        # # Send a JSON response with a trigger (running = False)
        # return jsonify({'running':False}) 


# Create new GET EndPoint to /setup
@app.route('/setup', methods=['GET'])
def setup():
    """
    A setup function from the GET endpoint.
    It will run all necessary functions to execute 
    the simulation setup (before the first iteration).

    It send to the client all necessary information for the 
    3D environment setup.
    """
    # Send JSON response about number of agents, and initial wealth,
    # taken from model parameters (model.p)
    return jsonify({'agents' : model.p.agents, 'wealths' : model.p.wealths})



#########################################################
#              Wealth Transfer Simulation               #
#########################################################

def gini(x):

    """ Calculate Gini Coefficient """
    # By Warren Weckesser https://stackoverflow.com/a/39513799

    x = np.array(x)
    mad = np.abs(np.subtract.outer(x, x)).mean()  # Mean absolute difference
    rmad = mad / np.mean(x)  # Relative mean absolute difference
    return 0.5 * rmad

class WealthModel(ap.Model):

    """ 
    A simple model of random wealth transfers. 

    Here we have the same good old Wealth Model, but
    considering a list of all agents' action. Additionally,
    It needs to verify when to stop manually (inside update()).
    """

    def setup(self):

        # Define a list of next actions from all agents  
        self.actions = []

        # Instantiate all agents (WealthAgents)
        self.agents = ap.AgentList(self,self.p.agents,WealthAgent)
        

    def step(self):

        # Reset the list of next actions
        self.actions = []

        # Call agents' step()
        self.agents.step()
        

    def update(self):

        # Record agents' Gini Coefficient
        self.record('Gini Coefficient', gini(self.agents.wealth))

        # If the simulation has reached max steps then stop simulation
        if self.t >= self._steps:
            self.stop()


    def end(self):

        # Reccord final wealth of all agents
        self.agents.record('wealth')

        # End of simulation message
        print(f"\nModel ended on step {self.t}\n")
        

class WealthAgent(ap.Agent):

    """
    An Agent with wealth.

    Here we have the same good old WealthAgent, but instead
    of executing the action here, it executes the action on 
    the client (Unity 3D).
    """

    def setup(self):

        # The initial wealth
        self.wealth = model.p.wealths
        

    def step(self):

        """ 
        The wealth transfer function.

        If the agent has wealth, then it will give a coin to a
        random partner. The action is saved into the list of 
        actions  (from the model), no executed.
        """

        if self.wealth > 0:

            # Select a random partner 
            # (and deconvert it from the AgentIter class)
            partner = self.model.agents.random().to_list()[0]

            # Save the 'action' of 'From whom give a coin'
            # by agent's id
            self.model.actions.append(self.id)

            # Save the 'action' of 'To who give a coin'
            # by agent's id
            self.model.actions.append(partner.id)
    

def simStop():

    """
    The procedure to be executed when the simulation stops.
    
    First, it calls the model's end() method,
    Then, it creates an output (the recorded data) (see the agentpy docs)
    Then, it creates figures to visualize data (just like the original model)
    """

    model.end() # The end method
    model.create_output() # Generating output from model

    # Getting 'results' from the model's output
    results = model.output

    # Visualize Gini Coefficient
    data = results.variables.WealthModel
    ax = data.plot()
    plt.show()

    # Visualize agent wealth accumulation
    sns.histplot(data=results.variables.WealthAgent, binwidth=1)
    plt.show()



#########################################################
#                          Main                         #
#########################################################

# main driver function
if __name__ == '__main__':

    # Definition of Model's parameters
    # Note: if you take out 'steps', the simulation will
    # run indefinitely 
    parameters = {
        'agents' : 100,
        'steps' : 100,
        'wealths' : 1
    }

    # Create model with parameters
    model = WealthModel(parameters)

    # Run the manual setup of the model 
    # (model.sim_setup(), instead of model.setup())
    model.sim_setup()

    # run() method of Flask class runs the application 
    # on the local development server.
    app.run() # http://localhost:5000

    # When the server stops, execute the stop procedure.
    simStop()
    