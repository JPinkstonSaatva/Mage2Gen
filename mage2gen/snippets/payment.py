# A Magento 2 module generator library
# Copyright (C) 2016 Derrick Heesbeen
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
import re
from .. import Module, Phpclass, Phpmethod, Xmlnode, StaticFile, Snippet, SnippetParam, Readme

class PaymentSnippet(Snippet):
	snippet_label = 'Payment Method'

	description = """Creates a payment method

	Generated Payment methods can be found in *Magento Adminpanel > Stores > Settings > Configuration > Sales > Payment Methods*

	It allows you to add extra payment methods to Magento. For example if you need to have a payment method which can only be used in the backend
	or if you need a payment that directly creates an invoice.

	Input for the payment method

	"""

	def add(self, method_name, credit_card, extra_params=None):
		def camel_to_snake(name):
			name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
			return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

		payment_code = camel_to_snake(method_name)
		payment_class_name = method_name


		if credit_card:
			payment_class = Phpclass('Model\\Payment\\'+payment_class_name,
				extends='\Magento\Payment\Model\Method\Cc',
				attributes=[
					'protected $_code = "'+payment_code+'";'
				])
		else:
			payment_class = Phpclass('Model\\Payment\\'+payment_class_name,
				extends='\Magento\Payment\Model\Method\AbstractMethod',
				attributes=[
					'protected $_code = "'+payment_code+'";',
				])

		if credit_card:
			payment_class.add_method(Phpmethod(
				'capture',
				params=[
					'\\Magento\\Payment\\Model\\InfoInterface $payment',
					'$amount'
				],
				body="""
					try {
						//check if payment has been authorized
						if(is_null($payment->getParentTransactionId())) {
							$this->authorize($payment, $amount);
						}

						//build array of payment data for API request.
						$request = [
							'capture_amount' => $amount,
							//any other fields, api key, etc.
						];

						//make API request to credit card processor.
						$response = $this->makeCaptureRequest($request);

						//todo handle response

						//transaction is done.
						$payment->setIsTransactionClosed(1);

					} catch (\Exception $e) {
						$message = $e->getMessage();
						$this->debug($payment->getData(), $message);
					}

					return $this;
						"""
			))

			payment_class.add_method(Phpmethod(
				'authorize',
				params=[
					'\\Magento\\Payment\\Model\\InfoInterface $payment',
					'$amount'
				],
				body="""
					try {

						///build array of payment data for API request.
						$request = [
							'cc_type' => $payment->getCcType(),
							'cc_exp_month' => $payment->getCcExpMonth(),
							'cc_exp_year' => $payment->getCcExpYear(),
							'cc_number' => $payment->getCcNumberEnc(),
							'amount' => $amount
						];

						//check if payment has been authorized
						$response = $this->makeAuthRequest($request);

					} catch (\Exception $e) {
						$message = $e->getMessage();
						$this->debug($payment->getData(), $message);
					}

					if(isset($response['transactionID'])) {
						// Successful auth request.
						// Set the transaction id on the payment so the capture request knows auth has happened.
						$payment->setTransactionId($response['transactionID']);
						$payment->setParentTransactionId($response['transactionID']);
					}

					//processing is not done yet.
					$payment->setIsTransactionClosed(0);

					return $this;
			"""
			))

			payment_class.add_method(Phpmethod(
				'getConfigPaymentAction',
				body='return self::ACTION_AUTHORIZE;'
			))

			payment_class.add_method(Phpmethod(
				'makeAuthRequest',
				params=['$request'],
				body="""
					$response = ['transactionId' => 123]; // TODO: implement API call for auth request.

					if(!$response) {
						throw new \Magento\Framework\Exception\LocalizedException(__('Failed auth request.'));
					}

					return $response;
				"""
			))

			payment_class.add_method(Phpmethod(
				'makeCaptureRequest',
				params=['$request'],
				body="""
					$response = ['success']; // TODO: implement API call for capture request.

					if(!$response) {
						throw new \Magento\Framework\Exception\LocalizedException(__('Failed capture request.'));
					}

					return $response;
				"""
			))

		self.add_class(payment_class)

		if credit_card:
			di_file = 'etc/adminhtml/di.xml'

			di = Xmlnode('config', attributes={'xsi:noNamespaceSchemaLocation':"urn:magento:framework:ObjectManager/etc/config.xsd"},nodes=[
				Xmlnode('type', attributes={'name':'Magento\Payment\Model\CcGenericConfigProvider'},nodes=[
					Xmlnode('arguments',nodes=[
						Xmlnode('argument',attributes={'name':'methodCodes','xsi:type':'array'},nodes=[
							Xmlnode('item',attributes={'name':payment_code,'xsi:type':'const'},node_text=payment_class.class_namespace + '::CODE')
						])
					])
				])
			])

			self.add_xml(di_file, di)

		config_file = 'etc/config.xml'

		if creditcard:
			cc_node = Xmlnode('cctypes', node_text='yadayada')
		else:
			cc_node = None

		config = Xmlnode('config',attributes={'xsi:noNamespaceSchemaLocation':"urn:magento:module:Magento_Store:etc/config.xsd"},nodes=[
				Xmlnode('default',nodes=[
					Xmlnode('payment',nodes=[
						Xmlnode(payment_code,nodes=[
							Xmlnode('title',node_text=method_name),
							Xmlnode('model',node_text= payment_class.class_namespace),
							Xmlnode('active',node_text='1'),
							Xmlnode('order_status',node_text='pending'),
							cc_node
						])
					])
				])
			]);

		self.add_xml(config_file, config)

		system_file = 'etc/adminhtml/system.xml'

		if credit_card:
			cctypes_node = Xmlnode('cctypes', attributes={'id':'cctypes', 'type':'multiselect', 'sortOrder':65,'showInDefault':1,'translate':'label'},match_attributes={'id'},nodes=[
								Xmlnode('label',node_text='Credit Card Types'),
								Xmlnode('source_model',node_text='Magento\Payment\Model\Source\Cctype'),
							])
		else:
			cctypes_node = None

		system = Xmlnode('config', attributes={'xsi:noNamespaceSchemaLocation':"urn:magento:module:Magento_Config:etc/system_file.xsd"}, nodes=[
				Xmlnode('system',  nodes=[
					Xmlnode('section',attributes={'id':'payment','sortOrder':1000,'showInDefault':1,'translate':'label'},match_attributes={'id'},nodes=[
						Xmlnode('group', attributes={'id':payment_code,'sortOrder':10,'showInDefault':1,'translate':'label'},match_attributes={'id'},nodes=[
							Xmlnode('label',node_text=method_name),
							Xmlnode('field', attributes={'id':'active','type':'select','sortOrder':10,'showInDefault':1,'translate':'label'},match_attributes={'id'},nodes=[
								Xmlnode('label',node_text='Enabled'),
								Xmlnode('source_model',node_text='Magento\\Config\\Model\\Config\\Source\\Yesno'),
							]),
							Xmlnode('field', attributes={'id':'title','type':'text','sortOrder':20,'showInDefault':1,'translate':'label'},match_attributes={'id'},nodes=[
								Xmlnode('label',node_text='Title'),
							]),
							cctypes_node
						])
					])
				])
		])

		self.add_xml(system_file,system)

		self.add_static_file(
			'.',
			Readme(
				specifications=" - Payment Method\n\t- {}".format(method_name),
				configuration=" - {} - payment/{}/*".format(method_name, payment_code)
			)
		)
	@classmethod
	def params(cls):
		return [
			SnippetParam(
				name='method_name',
				required=True,
				description='Example: Invoice, Credits',
				regex_validator= r'^[a-zA-Z]{1}[a-zA-Z0-9_]+$',
				error_message='Only alphanumeric and underscore characters are allowed, and need to start with a alphabetic character.'),
			SnippetParam(
				name='credit_card',
				description='Credit Card Payment Method',
                default=False,
                yes_no=True)
		]
