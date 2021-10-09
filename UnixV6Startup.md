How does Unixv6 start?

The OS starts at line 0612 in the source. At this point in time, the machine (presumably a PDP 11/40 or something similar) has nothing initialized. The goal of the Unixv6 start
sequence is to initialize a couple of things:

  <li> The segmentation registers for user space and kernel space. These segmentation registers actually refer 
        to a pair of registers: the page address register (the PAR) and the page descriptor register (the PDR). 
	The page address register is used to decode virtual addresses into physical ones (with the caveat that 
	this translation only occurs if the memory management unit is on). The layout of the PAR is as follows:
        
        <img>PAR.png</img>

        The PDR, on the other hand, specifies the length of the memory area (called a page - more on that later). 
	The PDR also specifies permissions that control memory access. The layout of the PDR is below:

	<img>PDR.png></img>

	As mentioned above, the machine actually keeps two sets of segmentation registers - one for when the
	machine is in user mode, and another for one the machine is in kernel mode. The mode of the machine
	is determined by a register called the Processor Status Word (PS) - but more on that later.

	<img>segmentation_regs.png></img>

        Setting the segmentation registers up appropriately will help ensure a clean split between user space
	and kernel space. This setup is also relevant once we start delving into process memory. </li>
