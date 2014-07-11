### vcweb 
vcweb is a Python/Django framework that purportedly helps developers build interactive web-based experiments for collective action researchers interested in social ecological systems. 
We maintain a managed instance of vcweb at https://vcweb.asu.edu but you are welcome to host your own server.

### features
* Web based experiment parameterization, with support for experiment-wide parameters and round-specific parameters.
  Standard parameters include show up fees, an exchange rate for tokens to currency, round durations, and group size.
  Custom parameters are defined by experiment developers; examples include initial resource levels and regrowth factors
  for common pool resource game. An experiment treatment consists of an ordered set of round parameterizations. Each
  round parameterization can be specified to repeat N times as well.
* Support for two classes of experiments:
    - controlled experiments typically run in a computer lab with "captive" participants. These experiments are
      characterized by timed rounds of parameterizable duration, and round transitions manually managed by an
      experiment facilitator (with ongoing development to properly implement automated round transitions)
    - extended experiments spanning multiple days or weeks with cron-based scheduled custom experiment logic (e.g., at
      midnight perform some calculations, determine the current state of a resource and payments and send summary emails
      to all registered participants). Round transitions occur at some defined interval, e.g., at midnight.
* Subject pool management and randomized invitation / recruitment with custom invitation emails
* Flexible data model that captures Experiments, ExperimentConfigurations, RoundConfigurations, and arbitrary experiment
  data via the [Entity Attribute Value Model](http://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model)
  to capture participant-specific data and group-specific data. Work is ongoing to simplify and improve this API.
* Real-time chat and server push via [sockjs-tornado](https://github.com/mrjoes/sockjs-tornado)
* Existing experiment UIs have been implemented using [Bootstrap 3](http://getbootstrap.com) and
  [knockout](http://knockoutjs.com) but the view layer is unopinionated and experiments can implement any browser based
  UI. Try [reactjs](http://facebook.github.io/react/) and [Om](https://github.com/swannodette/om),
  [angular](https://angularjs.org/), [emberjs](http://emberjs.com/), javascript / canvas libraries like
  [d3js](http://d3js.org/) or [processingjs](http://ejohn.org/blog/processingjs/). You'll still have to deal with
  Python/Django on the server side though.

### run an experiment

In order to run a vcweb experiment you'll need an experimenter account. Please [contact us](http://vcweb.asu.edu/contact)
if you'd like to request an experimenter account. 

### participate in an experiment

In order to participate in a vcweb experiment you must be invited to one by an experimenter. 

### develop an experiment or contribute to the infrastructure
[![Build Status](https://drone.io/bitbucket.org/virtualcommons/vcweb/status.png)](https://drone.io/bitbucket.org/virtualcommons/vcweb/latest)
For more information on how to install and deploy the software please visit <https://bitbucket.org/virtualcommons/vcweb/wiki/Home>

