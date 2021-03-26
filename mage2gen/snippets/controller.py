# A Magento 2 module generator library
# Copyright (C) 2016 Maikel Martens
# Copyright (C) 2016 Derrick Heesbeen Added Ajax Controller
#
# This file is part of Mage2Gen.
#
# Mage2Gen is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import os
import textwrap
from .. import Module, Phpclass, Phpmethod, Xmlnode, StaticFile, Snippet, SnippetParam, Readme

class ControllerSnippet(Snippet):
	description = """
	Controller is used to serve a request path. A request path look like this:

		www.yourmagentoinstallation.com/frontname/section/action

	- **frontname:** Configured in the router.xml and must be unique.
	- **section:** Is a subfolder or folders to the action class.
	- **action:** An action class that will execute the reqeust.

	This snippet will also create a layout.xml, Block and phtml for the action.
	"""

	def add(self, frontname='', section='index', action='index', ajax=False, extra_params=None, has_menu=True, top_level_menu=True, requires_url_params=False):
		if not frontname:
			frontname = '{}_{}'.format(self._module.package.lower(),self._module.name.lower())
		file = 'etc/{}/routes.xml'.format('adminhtml')

		# Create config router
		module = Xmlnode('module', attributes={'name': self.module_name})
		module.attributes['before'] = 'Magento_Backend'

		config = Xmlnode('config', attributes={'xsi:noNamespaceSchemaLocation':"urn:magento:framework:App/etc/routes.xsd"}, nodes=[
			Xmlnode('router', attributes={'id': 'admin'}, nodes=[
				Xmlnode('route', attributes={'id': frontname, 'frontName': frontname}, nodes=[
					module
				])
			])
		])
		self.add_xml(file, config)

		# Handy re-used vars
		block_name = "{}.{}".format(section, action)

		# Create controller
		controller_class = ['Controller']
		controller_class.append('Adminhtml')
		controller_class.append(section)
		controller_class.append(action)

		controller_extend = '\Magento\Backend\App\Action'
		controller = Phpclass('\\'.join(controller_class), controller_extend, attributes=[
			'protected $resultPageFactory;'
		])

		if ajax:
			controller.attributes.extend([
			'protected $jsonHelper;'
		])

		# generate construct
		context_class = '\Magento\\' + ('Backend') +'\App\Action\Context'
		if ajax:
			controller.add_method(Phpmethod(
				'__construct',
				params=[
					context_class + ' $context',
					'\Magento\Framework\View\Result\PageFactory $resultPageFactory',
					'\Magento\Framework\Json\Helper\Data $jsonHelper',
					'\Psr\Log\LoggerInterface $logger',
				],
				body="""$this->resultPageFactory = $resultPageFactory;
					$this->jsonHelper = $jsonHelper;
					$this->logger = $logger;
					parent::__construct($context);
				""",
				docstring=[
					'Constructor',
					'',
					'@param ' + context_class + '  $context',
					'@param \\Magento\\Framework\\Json\\Helper\\Data $jsonHelper',
				]
			))
		else:
			controller.add_method(Phpmethod(
				'__construct',
				params=[
					context_class + ' $context',
					'\Magento\Framework\View\Result\PageFactory $resultPageFactory'
				],
				body="""$this->resultPageFactory = $resultPageFactory;
					parent::__construct($context);
				""",
				docstring=[
					'Constructor',
					'',
					'@param ' + context_class + '  $context',
					'@param \\Magento\\Framework\\View\\Result\\PageFactory $resultPageFactory',
				]
			))

		# generate execute method
		if ajax:
			execute_body = """try {
			    return $this->jsonResponse('your response');
			} catch (\Magento\Framework\Exception\LocalizedException $e) {
			    return $this->jsonResponse($e->getMessage());
			} catch (\Exception $e) {
			    $this->logger->critical($e);
			    return $this->jsonResponse($e->getMessage());
			}
        	"""
		else:
			if requires_url_params:
				execute_body = textwrap.dedent("""\
												$resultPage = $this->resultPageFactory->create();
												// TODO: Do controllery things, like:
												//       - Validate and sanitize params, maybe redirect if invalid.
												//       - Set the resulting clean data on the block for direct access.
												//       - You can even create a class for this data to enforce structure!
												$block = $resultPage->getLayout()->getBlock('{}');
												$params = $this->getRequest()->getParams();
												$block->setData('params', $params);
												return $resultPage;
                        						""").format(block_name)
			else:
				execute_body = 'return $this->resultPageFactory->create();'

		controller.add_method(Phpmethod(
			'execute',
			body=execute_body,
			docstring=[
				'Execute view action',
				'',
				'@return \Magento\Framework\Controller\ResultInterface',
			]
		))

		# generate jsonResponse method
		if ajax:
			controller.add_method(Phpmethod(
				'jsonResponse',
				params=["$response = ''"],
				body="""
				return $this->getResponse()->representJson(
				    $this->jsonHelper->jsonEncode($response)
				);""",
				docstring=[
					'Create json response',
					'',
					'@return \Magento\Framework\Controller\ResultInterface',
				]
				)
			)

		self.add_class(controller)

		if ajax:
			return
		else:
			# create block
			block_class = ['Block']
			block_method_name = 'getSomeData'
			block_class.append('Adminhtml')
			block_class.append(section)
			block_class.append(action)

			block_extend = '\Magento\Backend\Block\Template'
			block = Phpclass('\\'.join(block_class), block_extend)

			block_context_class = '\Magento\Backend\Block\Template\Context'
			block.add_method(Phpmethod(
				'__construct',
				params=[
					block_context_class + ' $context',
					'array $data = []',
				],
				body="""parent::__construct($context, $data);""",
				docstring=[
					'Constructor',
					'',
					'@param ' + block_context_class + '  $context',
					'@param array $data',
				]
			))

			method_body = ""
			if requires_url_params:
				method_body = textwrap.dedent("""
												// TODO: Do something useful and return something helpful, even leverage data passed from the controller
												$params = $this->getData('params');
												return "I has params, don't you know:<br/>" . print_r($params, true);
												""")
			else:
				method_body = textwrap.dedent("""
												// TODO: Do something useful and return something helpful
												return 'Abracadabra!';
												""")

			block.add_method(Phpmethod(
				block_method_name,
				body=method_body,
				docstring=[
					'Utility to grab some data for inclusion in a template',
					'@return mixed'
				]
			))

			self.add_class(block)

			# Add layout xml
			layout_xml = Xmlnode('page', attributes={'layout':"admin-1column", 'xsi:noNamespaceSchemaLocation':"urn:magento:framework:View/Layout/etc/page_configuration.xsd"}, nodes=[
				Xmlnode('body', nodes=[
					Xmlnode('referenceContainer', attributes={'name': 'content'}, nodes=[
						Xmlnode('block', attributes={
							'name': block_name,
							'class': block.class_namespace,
							'template': "{}::{}/{}.phtml".format(self.module_name, section, action)
						})
					])
				])
			])
			path = os.path.join('view', 'adminhtml', 'layout', "{}_{}_{}.xml".format(frontname, section, action))
			self.add_xml(path, layout_xml)

			# add template file
			path = os.path.join('view', 'adminhtml', 'templates')
			body_text = textwrap.dedent("""\
										<?php
										/**
										 * @var $block \{classname}
										 */
										?>
										<div>
											<?= __('<strong>The template says:</strong><br/><em>Hello {section}::{action}</em>') ?>
											<br/><br/>
											<strong>The block says:</strong><br/><em><?= $block->{function_name}() ?></em>
										</div>
										""").format(
														classname=block.class_namespace,
														function_name=block_method_name,
														section=section,
														action=action
													)

			self.add_static_file(path, StaticFile("{}/{}.phtml".format(section, action),body=body_text))

			if has_menu:
				# create menu.xml
				top_level_menu_node = False
				if top_level_menu:
					top_level_menu_node = Xmlnode('add', attributes={
						'id': "{}::top_level".format(self._module.package),
						'title': self._module.package,
						'module': self.module_name,
						'sortOrder': 9999,
						'resource': 'Magento_Backend::content',
					})

				self.add_xml('etc/adminhtml/menu.xml', Xmlnode('config', attributes={
					'xsi:noNamespaceSchemaLocation': "urn:magento:module:Magento_Backend:etc/menu.xsd"}, nodes=[
					Xmlnode('menu', nodes=[
						top_level_menu_node,
						Xmlnode('add', attributes={
							'id': '{}::{}_{}'.format(self.module_name, section, action),
							'title': "{} {}".format(section.replace('_', ' '), action.replace('_', ' ')),
							'module': self.module_name,
							'sortOrder': 9999,
							'resource': '{}::{}_{}'.format(self.module_name, section, action),
							'parent': '{}::top_level'.format(self._module.package,frontname),
							'action': '{}/{}/{}'.format(frontname, section, action)
						})
					])
				]))


				acl_xml = Xmlnode('config', attributes={'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance','xsi:noNamespaceSchemaLocation':"urn:magento:framework:Acl/etc/acl.xsd"}, nodes=[
					Xmlnode('acl',nodes=[
						Xmlnode('resources',nodes=[
							Xmlnode('resource',attributes={'id':'Magento_Backend::admin'},nodes=[
								Xmlnode('resource',attributes={'id':'{}::{}'.format(self.module_name, frontname),'title':'{}'.format(frontname.replace('_', ' ')),'sortOrder':"10"}, nodes=[
									Xmlnode('resource',attributes={'id':'{}::{}_{}'.format(self.module_name, section, action),'title':'{} {}'.format(section.replace('_', ' '), action.replace('_', ' ')),'sortOrder':"10"}),
								])
							])
						])
					])
				])

				self.add_xml('etc/acl.xml', acl_xml)

		self.add_static_file(
			'.',
			Readme(
				specifications=" - Controller\n\t- {} > {}/{}/{}".format('adminhtml', frontname, section, action),
			)
		)


	@classmethod
	def params(cls):
		return [
			SnippetParam(name='frontname', required=False, description='On empty uses module name in lower case',
				regex_validator= r'^[a-z]{1}[a-z0-9_]+$',
				error_message='Only lowercase alphanumeric and underscore characters are allowed, and need to start with a alphabetic character.',
				repeat=True),
			SnippetParam(name='section', required=True, default='index',
				regex_validator= r'^[a-z]{1}[a-z0-9_]+$',
				error_message='Only lowercase alphanumeric and underscore characters are allowed, and need to start with a alphabetic character.',
				repeat=True),
			SnippetParam(name='action', required=True, default='index',
				regex_validator= r'^[a-z]{1}[a-z0-9_]+$',
				error_message='Only lowercase alphanumeric and underscore characters are allowed, and need to start with a alphabetic character.'),
			SnippetParam(name='ajax', yes_no=True),
			SnippetParam(name='has_menu', yes_no=True, default=True),
			SnippetParam(
				name='top_level_menu',
				yes_no=True,
				default=True,
				repeat=True
			),
			SnippetParam(
				name='requires_url_params',
				yes_no=True,
				default=False
			)
		]
